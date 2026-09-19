# Hello Robot

Hello Robot WatcheRobot Application.

- Application ID: `local.hello_robot`
- Author: Local Developer

## Develop

```powershell
watcherobot robot setup  # first robot only
watcherobot robot status
watcherobot app run
watcherobot app check .
watcherobot app publish .
```

The generated `app.py` always logs a Hello World success. With a compatible
robot connected, it also plays the `happy` behavior once. Run it through the
SDK Runtime; do not execute `app.py` directly.
