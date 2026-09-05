import { ref, watch } from "vue";

const translations = {
  fr: {
    title: "Système de prédiction du risque d'inondation",
    predict: "Lancer la prédiction",
    mapTitle: "Carte des quartiers vulnérables",
    loading: "Chargement...",
    error: "Une erreur est survenue",
    welcomeTitle: "Bienvenue sur ARO.ai",
    welcomeSubtitle: "Anticipez les risques d'inondation à Ambohimanambola",
    welcomeStart: "Commencer",
  },
  mg: {
    title: "Rafitra fanombanana ny loza mety hiseho amin'ny tondra-drano",
    predict: "Atomboy ny vinavina",
    mapTitle: "Sarintanin'ny fokontany mora voa",
    loading: "Eo am-pandehanana...",
    error: "Nisy olana",
    welcomeTitle: "Tongasoa eto amin'ny ARO.ai",
    welcomeSubtitle: "Vinavino mialoha ny loza amin'ny tondra-drano ao Ambohimanambola",
    welcomeStart: "Manomboka",
  },
};

// État module-level partagé par toute l'appli (pas besoin de Pinia ici).
const lang = ref(localStorage.getItem("lang") || "fr");

watch(lang, (value) => {
  localStorage.setItem("lang", value);
});

export function useLanguage() {
  const t = (key) => translations[lang.value]?.[key] ?? key;
  const toggleLang = () => {
    lang.value = lang.value === "fr" ? "mg" : "fr";
  };
  return { lang, t, toggleLang };
}