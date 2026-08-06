// Pulls the python runtime the browser will load, into static/. Everything is served
// from our own origin : a page that depends on a cdn stops working the day it moves
import { createWriteStream } from "node:fs";
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "..", "static", "runtime");

// where each piece comes from, in its own fichier so a version bump is one edit and
// never a hunt through the code. defusedxml is pure python and absent from the
// distribution, it comes straight off pypi
const SOURCES = JSON.parse(await readFile(join(HERE, "runtime.sources.json"), "utf-8"));

const VERSION = SOURCES.version;
const BASE = SOURCES.distribution;
const RUNTIME = SOURCES.runtime;
const PYPI = SOURCES.elsewhere;


async function grab(url, into)
{
    const answer = await fetch(url);
    if (!answer.ok)
    {
        throw new Error(`${url} a repondu ${answer.status}`);
    }

    await pipeline(Readable.fromWeb(answer.body), createWriteStream(into));
}


async function alreadyThere(path)
{
    try
    {
        const info = await stat(path);
        return info.size > 0;
    }
    catch
    {
        return false;
    }
}


await mkdir(TARGET, { recursive: true });

const shopping = RUNTIME.map(name =>
{
    return [name, BASE + name];
}).concat(Object.entries(PYPI));

const results = await Promise.all(shopping.map(async ([name, url]) =>
{
    const into = join(TARGET, name);
    if (await alreadyThere(into))
    {
        return false;
    }

    await grab(url, into);
    console.log(`  ${name}`);
    return true;
}));

const fetched = results.filter(Boolean).length;

// the loader reads this, it carries no second copy of the file names
const found = await readdir(TARGET);
const wheels = found.filter(name =>
{
    return name.endsWith(".whl");
});
wheels.sort();
await writeFile(join(TARGET, "wheels.json"),
                JSON.stringify({ version: VERSION, wheels }, null, 2));

const sizes = await Promise.all(found.map(async name =>
{
    return (await stat(join(TARGET, name))).size;
}));

const total = sizes.reduce((sum, size) =>
{
    return sum + size;
}, 0);

console.log(`runtime : ${fetched} fichier(s) recuperes, ${(total / 1048576).toFixed(1)} Mo au total`);
