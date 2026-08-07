// Copies core/ and cli/ into static/. The browser mounts the very same modules the
// command line runs, no second implementation to drift
import { mkdir, readdir, copyFile, rm, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PROJECT = resolve(HERE, "..", "..");
const TARGET = resolve(HERE, "..", "static", "engine");

const PACKAGES = ["core", "cli"];

await rm(TARGET, { recursive: true, force: true });

const listed = await Promise.all(PACKAGES.map(async name =>
{
    const from = join(PROJECT, name);
    const into = join(TARGET, name);
    await mkdir(into, { recursive: true });

    const found = await readdir(from);
    const modules = found.filter(file =>
    {
        return file.endsWith(".py");
    });
    modules.sort();

    await Promise.all(modules.map(file =>
    {
        return copyFile(join(from, file), join(into, file));
    }));

    console.log(`  ${name} : ${modules.length} modules`);
    return [name, modules];
}));

const manifest = Object.fromEntries(listed);

// the parcours live in data/ with the rest of the reference data, and are copied for
// the same reason core/ is : one list, never two
await copyFile(join(PROJECT, "data", "presets.json"),
               resolve(HERE, "..", "src", "lib", "core", "presets.json"));
console.log("  presets recopies depuis data/");

// the worker reads this to know what to write into the virtual filesystem. A hand kept
// list would rot the first time a module is added
await writeFile(join(TARGET, "manifest.json"), JSON.stringify(manifest, null, 2));
