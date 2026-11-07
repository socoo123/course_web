import { useSyncExternalStore } from "react";

const KEY = "cw:theme";
const EVENT = "cw:theme";

function isDark() {
  return document.documentElement.classList.contains("dark");
}

function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  return () => window.removeEventListener(EVENT, cb);
}

export function useDark(): boolean {
  return useSyncExternalStore(subscribe, isDark, () => false);
}

export function toggleTheme() {
  const dark = !isDark();
  document.documentElement.classList.toggle("dark", dark);
  localStorage.setItem(KEY, dark ? "dark" : "light");
  window.dispatchEvent(new Event(EVENT));
}
