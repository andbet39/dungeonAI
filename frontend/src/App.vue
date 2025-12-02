<template>
  <router-view />
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Dark mode class for PrimeVue */
.dark-mode {
  background: var(--p-surface-0);
  color: var(--p-text-color);
}
</style>
