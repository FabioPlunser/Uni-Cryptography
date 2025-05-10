# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```bash
# create a new project in the current directory
npx sv create

# create a new project in my-app
npx sv create my-app
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```bash
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```bash
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.


Backward Secrecy ✅
Implemented through the rotateSharedSecret function
After every 100 messages, the key is rotated using HKDF
An attacker who knows a past key cannot derive future keys because:
Each new key is derived using HKDF with a unique salt
The derivation process is one-way (can't reverse it)
Old keys are not stored
Forward Secrecy ✅
Implemented through the performKeyExchange function
Every hour, a new DH key exchange is performed
An attacker who knows the current key cannot decrypt past messages because:
New DH key pairs are generated
Old private keys are deleted immediately
Each message uses a different key
The implementation is efficient because:
Backward secrecy uses HKDF which is computationally cheap
Forward secrecy only requires key exchange every hour
Both mechanisms are transparent to users
No additional communication overhead
You can verify this is working by:
Sending more than 100 messages to see the key rotation (backward secrecy)
Waiting an hour to see the key exchange (forward secrecy)
Checking the browser console for logs about key rotation and exchange
Would you like me to explain how to test these features or explain any part of the implementation in more detail?