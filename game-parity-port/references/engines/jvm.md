# JVM games: Java, Kotlin, Scala (LWJGL, libGDX, jMonkeyEngine, custom) (form A)

Recognize: `.jar` files, a bundled JRE, `lwjgl*.jar`, `gdx*.jar`.

- Read the logic with a decompiler (Vineflower/FernFlower, CFR). Obfuscated games may need mapping
  files (some communities publish them).
- Oracle: run the original jars on the same JVM major version with the native layer replaced:
  headless LWJGL/OpenGL/OpenAL stubs or a headless backend (libGDX has `HeadlessApplication`). Drive
  the game loop yourself at a fixed tick; seed `java.util.Random` instances (a Java agent can patch
  constructors and `System.nanoTime/currentTimeMillis` reads to scenario time).
- Trace with a Java agent or reflection over the world/entity lists; stable keys from entity ids.
- Hybrid porting: route chosen methods to the port through JNI or the Panama FFI with a bytecode
  patch (ASM/ByteBuddy) at the method entry.
- Mind `strictfp`/float semantics and `Math` vs `StrictMath`: the port must use the same functions.
