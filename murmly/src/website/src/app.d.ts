// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	export interface UserCreate {
		username: string;
		password: string;
	}

	export interface User {
		username: string;
		public_key_b64: string;
		is_online: boolean;
		isAuthenticated: boolean;
		token: string;
	}

	export interface Token {
		access_token: string;
		token_type: string;
	}

	export interface PublicKeyUpdateData {
		public_key: string;
	}

	export interface AuthState {
		username: string | null;
		token: string | null;
		isAuthenticated: boolean;
	}
}

export { };
