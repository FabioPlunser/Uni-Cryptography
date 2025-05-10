<script lang="ts">
  import { authStore } from "$lib/stores/auth.svelte";
  import { cryptoStore } from "$lib/stores/crypto.svelte";
  import { errorStore } from "$lib/stores/error.svelte";

  async function handleSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    let username = String(formData.get("username"));
    let password = String(formData.get("password"));

    if (event.submitter.name === "login") {
      login(username, password);
    } else if (event.submitter.name === "register") {
      register(username, password);
    }
  }
  async function login(username: string, password: string) {
    await authStore.login(username, password);
  }

  async function register(username: string, password: string) {
    authStore.register(username, password);
  }
</script>

<div class="flex flex-col items-center justify-center h-screen">
  <form class="bg-base-200 p-4 rounded-2xl shadow-2xl" onsubmit={handleSubmit}>
    <fieldset class="fieldset">
      <legend class="fieldset-legend">Username</legend>
      <input
        name="username"
        required
        type="text"
        class="input"
        placeholder="Type here"
      />
    </fieldset>
    <fieldset class="fieldset">
      <legend class="fieldset-legend">Password</legend>
      <input
        name="password"
        required
        type="password"
        class="input"
        placeholder="Type here"
      />
    </fieldset>
    <br />
    <div class="flex gap-4 justify-center">
      <button
        class="btn btn-primary flex justify-center"
        type="submit"
        name="login">Login</button
      >
      <button
        class="btn btn-primary flex justify-center"
        type="submit"
        name="register">Register</button
      >
    </div>
  </form>
</div>
