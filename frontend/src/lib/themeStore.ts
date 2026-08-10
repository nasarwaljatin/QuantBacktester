// frontend/src/lib/themeStore.ts
import { create } from "zustand";

export interface ThemeState {
  theme: "light" | "dark";
  toggleTheme: () => void;
  setTheme: (theme: "light" | "dark") => void;
}

export const useThemeStore = create<ThemeState>()(() => ({
  theme: "dark",
  toggleTheme: () => {},
  setTheme: () => {},
}));

