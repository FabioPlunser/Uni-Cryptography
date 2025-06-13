
type Alert = {
  message: string;
  type: "info" | "success" | "warning" | "error"
}

function createAlertStore() {
  let alert: Alert = {
    message: "",
    type: "info"
  }
  let currentAlert = $state<Alert | null>(null)

  return {
    get current() {
      return currentAlert;
    },
    setAlert(message: string, type: "info" | "success" | "warning" | "error") {
      currentAlert = { message, type };
      setTimeout(() => {
        currentAlert = null;
      }, 1000);
    },
    clearAlert() {
      currentAlert = alert;
    },
    hasAlert() {
      return currentAlert !== null;
    },
    getAlert() {
      return currentAlert;
    }
  }
};


export const alertStore = createAlertStore()