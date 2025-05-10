
type Error = {
  message: string;
  code: number | string;
}

function createErrorStore() {
  let initError: Error = {
    message: "",
    code: 0
  }
  let currentError = $state<Error | null>(null)

  return {
    get current() {
      return currentError;
    },
    setError(message: string, code: number | string) {
      currentError = { message, code };
    },
    clearError() {
      currentError = null;
    },
    hasError() {
      return currentError !== null;
    },
    getError() {
      return currentError;
    }
  }
};


export const errorStore = createErrorStore()