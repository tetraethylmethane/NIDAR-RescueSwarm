# ground-station

The **Drikr NIDAR Ground Station** — mission view, telemetry, video, abort.

Code lives in [`tetraethylmethane/NIDAR-GSC`](https://github.com/tetraethylmethane/NIDAR-GSC);
this directory holds the engineering record. Mission-build rules that must not be
undone are in [`MISSION.md`](https://github.com/tetraethylmethane/NIDAR-GSC/blob/main/MISSION.md).

Requirements: **SYS-20, SYS-23, SYS-25, SYS-26, SYS-27** — see
[`../docs/requirements/requirements-baseline.md`](../docs/requirements/requirements-baseline.md).

```bash
cd server && python -m pytest mission_tests -q     # 107 tests
python utils/slippy_map_getter.py --verify         # offline tiles intact
./scripts/check-no-network.sh                      # rule 8.4 guard
python scripts/sim_mission.py --speed 8            # 3 drones, no aircraft
```

---

## Status

| Requirement | State |
|---|---|
| No external network (SYS-23, rule 8.4) | ✅ Poller removed, CI-guarded, tile cache tooling fixed |
| No mission-altering commands (SYS-20, rule 8.16) | ✅ Legacy blueprint **not registered**; dev UI not rendered |
| Single unified interface, 3 drones (SYS-25, rule 8.13) | ✅ MAVLink ingest, 3 SYSIDs → one `Fleet` |
| All eight rule 8.14 displays (SYS-26) | ✅ Built, rendered, **render-tested** |
| Three video feeds (SYS-27, rule 8.14) | ✅ Built · ⚠ MediaMTX never run |
| Abort and recall (rule 8.19) | ✅ Transmitting · ⚠ **no radio attached** |

**107 server tests · 16 component render tests · CI on all of it.** The mission
server now **starts** — verified by running it, not by importing it.

---

## The server had never actually started

That was the headline defect, and it was hidden by a test.

`app.py` → `apps.uav` → `handlers/uav.py` → `dronekit`, and DroneKit does
`collections.MutableMapping`, which moved to `collections.abc` in **Python
3.10**. The mission server could not boot on any current interpreter. The smoke
test had been installing a fake `dronekit` module to get around it — so the
suite passed on 3.12 while the program did not run on 3.12. A green tick over a
server nobody could start.

The fix was not to pin Python 3.9. **In a mission build the legacy `UAVHandler`
is redundant**: `mavlink_ingest.py` already carries position, mode, battery and
GNSS fix for all three aircraft over pymavlink, which DroneKit cannot do at all,
being single-vehicle by construction. Mission mode no longer imports
`apps.uav`, `apps.image` or `groundstation`, so DroneKit is **absent from the
process** rather than merely unused, and `app.gs` is `None`.

Nothing is stubbed in the smoke test any more, and it asserts
`"dronekit" not in sys.modules` directly. Absence is a fact about the running
process; "we do not call it" is only a claim about intent.

It settles SYS-20 more strongly too. The legacy blueprint's 31 routes — including
`/uav/commands/insert` and `/uav/commands/jump`, each a −50 under rule 8.16 —
are no longer in the URL map at all. Refusing a command is good; not having one
is better. The 403 guard stays as defence in depth, matching on path prefix so a
legacy path answers *"blocked in mission mode"* rather than a bare 404, which
would read as "wrong path, try another one".

Running it, for the first time:

```
GET  /                    200  Ground Station Backend
GET  /api/fleet           200  {"mission_mode":true,"phases":{"1":"IDLE",...
GET  /api/safety/status   200  {"state":"NO_RADIO","configured":false,...
POST /uav/arm             403  Blocked in mission mode
POST /uav/commands/insert 403  Blocked in mission mode
POST /api/safety/abort    503  state=NO_RADIO configured=False
dronekit in sys.modules : False        app.gs : None        python : 3.12.4
```

> **Known limitation, recorded not hidden.** The **dev** build
> (`MISSION_MODE=0`) still needs DroneKit and Python 3.9 —
> `mission_backend/dev_commands.py` is a route stub that acknowledges commands
> without sending them. Tolerable: the dev build is not the scored artefact and
> QGroundControl does bring-up better. `app.py` catches the import failure and
> prints the three options instead of a traceback about `MutableMapping`.

---

## The tile cache would have failed silently

`client/public/map` was empty, so with the network down the map is **blank** —
no boundary, no survivors, no aircraft. `slippy_map_getter.py` exists to prevent
that, and it had a defect that would only ever have surfaced on mission day.

**It wrote the response body to a `.png` without ever looking at it.** A 404
page, a rate-limit body or a truncated response landed on disk as a plausible
tile, and because the resume check was `os.path.isfile`, it was then skipped
forever. The cache would report complete, error never, and render grey squares
during a scored mission.

Every tile is now validated by magic number before it is written, written via a
temp file and rename so an interrupted run cannot leave a half-tile the resume
check trusts, and `--verify` re-checks what is already cached. **An empty cache
directory now fails verification** — the directory is created by the download
itself, so "it exists" proved nothing.

One trap found only by running it against the real server: **ArcGIS answers a
`.png` request with JPEG data.** Validating a PNG signature specifically — the
obvious way to write the check — rejects every real tile and caches nothing at
all, which is a worse failure than the original because it is total and silent.
The first version of this fix did exactly that, and downloaded 0 of 4 tiles.

It also no longer asks three interactive questions (so it can run from a script)
and no longer defaults to 38.14, −76.42, a field in Maryland left over from
AUVSI. `--dry-run` and `--verify` do not import `requests`, because needing an
HTTP library to check that *offline* tiles are intact would be a poor joke.

```bash
cd server
python utils/slippy_map_getter.py --center LAT,LON --radius-km 10 --zoom 10-18 --dry-run
python utils/slippy_map_getter.py --center LAT,LON --radius-km 10 --zoom 10-16 --yes
python utils/slippy_map_getter.py --verify
```

The dry run exists because **zoom 18 is most of the download**. Over a 10 km
radius, zoom 10–16 is ~1,700 tiles (~41 MB); adding 17 and 18 takes it to
~24,700 tiles (~600 MB) and roughly 50 minutes. Run it **weeks ahead** — the
mission area is not known until the KML arrives during setup, and there is no
network at the venue to fetch tiles with once you know where you are.

---

## The dev UI no longer renders in a mission build

`Servo`, `FlightPlanToolbar`, `Main` and the `Params` page still shipped. The
server refused them, so no rule was broken — that is not the argument. **A
control that silently does nothing is its own hazard:** under pressure someone
clicks *Write To*, sees no error, and believes the aircraft took it. The same
reasoning removed waypoint insertion from the map.

In a mission build the left column is **mission status and abort, and nothing
else**. `Params` refuses to render and says why, because `/params` is a URL and
browsers remember URLs. The legacy `/uav/quick` poll is switched off rather than
left hitting a dead path twice a second for eight minutes.

The client learns the mode from `mission_mode` on the `/api/fleet` snapshot, and
it defaults to **true** in every path — before the first poll returns, after the
backend goes away, and when the field is missing. Only an explicit `false`
unlocks anything.

Fixing this surfaced a latent bug in `useInterval`: it had no way to express
"not now", and `setInterval(fn, null)` coerces the delay to 0, which is a busy
loop rather than a stopped one. It also pinned the first render's closure
forever behind an empty dependency array, so a callback reading state saw its
initial value for the life of the component while looking perfectly correct.
Both fixed; every existing caller passes a constant delay and is unaffected.

---

## The components now actually render

Everything in `client/src/mission` had been written, compiled and shipped
**without a single component ever being mounted.** That is how two rule 8.14
displays came to be "built" while being referenced by zero files. A build proves
the syntax is valid; it proves nothing reaches a screen.

`@testing-library/react` was already in `devDependencies` and entirely unused.
**16 tests now mount `MissionStatus` and `AbortPanel` and read the resulting
DOM** — rule 8.14 items 1, 4, 6, 7 and 8 asserted as *visible text*, because a
jury looks at a screen, not at a JSON payload. Also covered: a non-RTK survivor
tag raises a visible warning; a stale display announces itself; the empty fleet
renders, which is the state at T-0 before the first MAVLink packet arrives, and
where a crash would mean a blank screen as the mission starts.

For abort specifically: no-radio reads *NOT IMPLEMENTED* rather than OK,
per-aircraft acknowledgement is displayed, and one click arms while transmitting
nothing — only the second click fires. Two-step confirm is easy to write and
easy to break; a refactor that hoists the fetch out of the confirm branch looks
harmless and turns a misclick during a nominal mission into an abort.

Writing these caught two mistakes in the *fixtures* rather than the code: a
delivery state that is not in `fleet.py`'s ladder, which would have passed
silently through a `|| state` fallback, and assertions using `getByText` where
two elements legitimately match.

**CI now runs all of it.** Nothing did before —
[`mission-build.yml`](https://github.com/tetraethylmethane/NIDAR-GSC/blob/main/.github/workflows/mission-build.yml)
runs the 107 server tests, the SYS-20 route check, `check-no-network.sh`, the
render tests and the client build, on **Python 3.12 with nothing stubbed**. It
asserts DroneKit is absent, `app.gs` is `None` and no `/uav` route exists.
Verified to *fail*: with the legacy blueprint re-registered, DroneKit reinserted
and `GroundStation` reconstructed, all three assertions trip. A guard that cannot
fail is not a guard.

---

## What is left

### Still never run as a system

- **MediaMTX has never been started.** The video path is unproven — `VideoWall`
  renders, but nothing has streamed through it.
- **Never connected to a real autopilot, or even SITL.** `mavlink_ingest` is
  tested against synthetic pymavlink messages.
- **The safety radio is not connected**, which abort correctly reports as
  `NO_RADIO` rather than pretending otherwise.
- **No tiles are cached on any machine yet** — the tooling is fixed and tested
  against the live server, but the venue coordinates are not known.
- **No browser has loaded the full page.** The components render under jsdom and
  the server runs; the two have not been put together with a human looking at
  the result.

### Needs hardware, versus does not

| Needs hardware | Does not |
|---|---|
| Safety radio bridge + aircraft receiver | ~~DroneKit out of the mission path~~ ✅ |
| Real autopilot telemetry | ~~Tile cache tooling~~ ✅ · ~~dev-UI gating~~ ✅ |
| Video end to end through MediaMTX | ~~Component render tests~~ ✅ · ~~CI~~ ✅ |
| Field validation | SITL instead of synthetic MAVLink · a full-stack local run |

**The next step is a full-stack local run** — `MISSION_MODE=1 python app.py`,
`npm start` and `sim_mission.py` together, with a browser open on the page. Both
halves now work in isolation and neither has met the other. After that, SITL in
place of the synthetic MAVLink messages. Both are free of aircraft; neither has
been done.

---

## How it works

**Two ingest paths, deliberately separate.** MAVLink via mavlink-router carries
position, mode, battery and GNSS fix. A 5 Hz JSON document over the mesh carries
region, task, detections and deliveries — MAVLink has no message for *"survivor
at lat/lon, confidence 0.91, confirmed over 7 frames, RTK-fixed"*, and bending
`NAMED_VALUE_FLOAT` into that shape is a trap.

**Mission mode is structural, not a flag.** `MISSION_MODE=1` (the default, so the
safe build is the default) never imports the command blueprint, and refuses every
state-changing method on the legacy `/uav` routes. A flag can be flipped by a
config file; an unimported module cannot be reached.

**Survivor dedup prefers fix quality over recency.** Two aircraft can see the same
survivor, and a later `RTK_FLOAT` tag is metres worse than an earlier
`RTK_FIXED` one. Ranking is fix → frames → confidence; confidence is last because
it is worth nothing in position terms.

**Abort is the secondary path.** The primary is `RC7_OPTION=4` driving the flight
controller directly, which survives a hung companion — and a hung companion is a
reason to abort. This layer adds addressing, acknowledgement and an audit trail.

---

## Verified without hardware

`sim_mission.py` flies three synthetic drones including the awkward cases — a
drone dropping off the mesh, a survivor re-tagged with a better fix by a
different aircraft, and a tag taken without RTK. Against a real `Fleet` and a
real socket:

```
datagrams accepted : 5287      rejected : 0
survivors found    : 6         kits delivered : 6
survivor 3 fix     : RTK_FIXED (drone 3)   ← dedup preferred fix over recency
warnings           : survivor 6 tagged without RTK (3D)
```

Both safety guards were verified to **fail** when the fault is reintroduced: a
command route forced into the mission build fails three tests, and a restored
ArcGIS URL fails the network check. A guard that cannot fail is not a guard.

---

## History

The inherited codebase and the three blockers it shipped with are archived in
[`../docs/gcs-inherited-review.md`](../docs/gcs-inherited-review.md). Worth
reading before adopting any other codebase written for a different competition.
