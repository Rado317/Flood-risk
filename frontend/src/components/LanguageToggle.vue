<script setup>
import { useLanguage } from "../composables/useLanguage";

const { lang, toggleLang } = useLanguage();
</script>

<template>
  <button @click="toggleLang" aria-label="Changer de langue">
    {{ lang === "fr" ? "FR → MG" : "MG → FR" }}
  </button>
</template>