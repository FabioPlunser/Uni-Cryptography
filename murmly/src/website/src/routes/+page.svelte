<script lang="ts">
  import { browser } from "$app/environment";
  import { onMount } from "svelte";
  import { auth, error } from "$lib/stores.svelte.ts";
  import { registerUser, loginForToken } from "$lib/apis";

  onMount(async () => {
    if (!browser) return;
  });

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
  async function login(username: string, password: string) {}

  async function register(username: string, password: string) {
    console.log("register", username, password);
    await registerUser(username, password);
  }
</script>

{#if error}
  <div class="alert alert-error">
    <div class="flex-1 text-2xl">
      <h1>{error.code}</h1>
      <h1>{error.message}</h1>
    </div>
  </div>
{/if}

{#if !auth?.isAuthenticated}
  <div class="flex flex-col items-center justify-center h-screen">
    <form
      class="bg-base-200 p-4 rounded-2xl shadow-2xl"
      onsubmit={handleSubmit}
    >
      <fieldset class="fieldset">
        <legend class="fieldset-legend">Username</legend>
        <input required type="text" class="input" placeholder="Type here" />
      </fieldset>
      <fieldset class="fieldset">
        <legend class="fieldset-legend">Password</legend>
        <input required type="text" class="input" placeholder="Type here" />
      </fieldset>
      <br />
      <div class="flex gap-4 justify-center">
        <button
          class="btn btn-primary flex justify-center"
          type="submit"
          name="login">login</button
        >
        <button
          class="btn btn-primary flex justify-center"
          type="submit"
          name="register">Register</button
        >
      </div>
    </form>
  </div>
{/if}
