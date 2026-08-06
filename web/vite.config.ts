import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// pages serves the site under the repository name, and nothing at the root
const BASE = (process.env.BASE_PATH ?? '') as '' | `/${string}`;

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// runes everywhere except in libraries, droppable once selte 6 lands
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// nothing runs on a server any more, the engine boots inside the browser
			adapter: adapter({ fallback: '404.html' }),
			paths: { base: BASE, relative: false },
			prerender: { entries: ['*'] }
		})
	]
});
