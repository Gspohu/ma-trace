import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite'; 
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// runes everywhere except in libraries, droppable once selte 6 lands
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// node adapter, the routing engine is spanwed as a child process at runtime
			adapter: adapter()
		}) 
	]
});
