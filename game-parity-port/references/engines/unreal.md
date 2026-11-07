# Unreal Engine (form B)

Recognize: `<Game>/Content/Paks/*.pak` (or `.utoc/.ucas`), `<Game>/Binaries/<Platform>/<Game>.exe`.
Gameplay is C++ and Blueprints; in shipping builds Blueprints are bytecode inside the paks, C++ is
native. The reflection system (UClass/UProperty/UFunction) is compiled into the binary.

- Extract assets and Blueprint bytecode with FModel / CUE4Parse / UAssetAPI (match the engine
  version and any pak encryption key the game ships). Blueprint bytecode can be disassembled
  (Kismet analyzers) to read the logic for porting.
- Oracle: run the shipping game with `-nullrhi -unattended -nosound`, a fixed timestep
  (`-benchmark -fps=60` or `FApp::SetUseFixedTimeStep`), and an injected module (UE4SS, a proxy DLL
  or a mod plugin) that each tick iterates `GUObjectArray`, and for actors/components of interest
  dumps every reflected UProperty by name. Feed scenario input through the Enhanced Input subsystem
  or by injecting key events. Seed `FMath::Rand`/`FRandomStream` if the game uses them.
- Physics (Chaos/PhysX) stays inside the oracle; physics parity for the port is a separate track.
- Verification is trace vs trace. Use stable keys from the actor's level path + component name.
