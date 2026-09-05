# EyeQ Flutter client

Drop the existing Flutter project here (the delivered `eyeq_flutter` tree),
keeping its own `pubspec.yaml` at this level:

```
services/frontend/
├── pubspec.yaml
├── lib/
│   ├── core/
│   ├── data/models/      <- generated from contracts/openapi.yaml
│   └── features/
│       ├── controller/   <- alert feed + evidence player
│       ├── professor/    <- engagement grid
│       └── admin/        <- seat calibration tool
└── test/
```

## Working against mocks
The backend emits mock alerts on `ws://localhost:8000/ws/session/{id}` from day
one. Build the full Controller flow against it — do not wait for models.

## FR6 in the UI
The alert card must not display, prefetch, or cache behavioral history. The
history call is fired only after the adjudication response returns 200.
