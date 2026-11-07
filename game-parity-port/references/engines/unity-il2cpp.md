# Unity (IL2CPP backend): instrumented original (form B)

Recognize: `GameAssembly.dll` / `libil2cpp.so` + `<Game>_Data/il2cpp_data/Metadata/global-metadata.dat`,
no `Assembly-CSharp.dll`. The C# logic is AOT-compiled to native code, but the metadata keeps every
type, field (with offsets) and method (with addresses).

- Recover layouts: Il2CppDumper or Cpp2IL produce class/field offsets, method RVAs, and dummy
  assemblies with the original names and signatures. Cpp2IL can also emit pseudo-IL/C# that is
  good enough to read the logic for porting, not to run it.
- Oracle: run the real game offline with a fixed timestep (`Time.captureDeltaTime` / a patched
  `Time.deltaTime`), vsync off, seeded `UnityEngine.Random` (hook `InitState`). Inject a module
  (BepInEx IL2CPP / MelonLoader, or a DLL proxy) that hooks the end of the frame, walks live objects
  through the IL2CPP runtime API (`il2cpp_object_get_class`, `il2cpp_field_get_value`) and writes the
  trace; the same module feeds scenario input (patch the Input System device state).
- Verification is trace vs trace (oracle run vs port run on the same scenario and seed). Hybrid
  porting inside the oracle is possible but harder: detour individual methods to the port with the
  injected module.
- The port itself is unaffected: it is written from the recovered logic and checked by the trace.
