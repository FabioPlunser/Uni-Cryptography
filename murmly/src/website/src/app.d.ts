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
		id: number;
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

	export interface CryptoState {
		dhParams: DHParameters | null;
		myDhPrivateKey: DHPrivateKey | null;
		myDhPublicKey: DHPublicKey | null;
		peerSharedSecrets: Map<string, CryptoKey>;
	}

	export interface Message {
		id?: string;
		sender: User;
		recipient: User;
		content: string;
		timestamp: string;
		isMine: boolean;
		delivered?: boolean;
		type?: "incoming" | "outgoing" | "status" | "error";
	}

	export interface WebSocketPayload {
		type?: "delivery_status";
		sender?: User;
		recipient: User;
		content?: string;
		timestamp: string;
		delivered?: boolean;
		error?: string;
		is_new_chat?: boolean;
	}

	export interface WebSocketMessage {
		type?: "delivery_status" | "error" | "message";
		sender?: string;
		recipient: string;
		content?: string;
		timestamp: string;
		delivered?: boolean;
		error?: string;
	}
}

export { };
