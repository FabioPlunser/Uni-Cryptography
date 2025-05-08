
type Auth = {
  username: string;
  isAuthenticated: boolean;
  token: string;
}

type Error = {
  message: string;
  code: number;
}

export const auth: Auth | null = $state(null)
export const cryptoStore = $state()
export const error: Error | null = $state(null)