// frontend/src/lib/themeStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ThemeState {
  theme: "light" | "dark";
  toggleTheme: () => void;
  setTheme: (theme: "light" | "dark") => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "dark", // default theme
      toggleTheme: () =>
        set((state) => {
          const nextTheme = state.theme === "dark" ? "light" : "dark";
          if (typeof window !== "undefined") {
            const html = document.documentElement;
            if (nextTheme === "dark") {
              html.classList.add("dark");
            } else {
              html.classList.remove("dark");
            }
          }
          return { theme: nextTheme };
        }),
      setTheme: (theme) =>
        set(() => {
          if (typeof window !== "undefined") {
            const html = document.documentElement;
            if (theme === "dark") {
              html.classList.add("dark");
            } else {
              html.classList.remove("dark");
            }
          }
          return { theme };
        }),
    }),
    {
      name: "theme-storage", // localStorage key
    }
  )
);
