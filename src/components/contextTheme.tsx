import { createContext, useContext } from "react";

export type Theme = "dark" | "light" | "system";

interface ThemeProviderState {
    theme: Theme
    setTheme: (theme: Theme) => void
}
   
export const ThemeProviderContext = createContext<ThemeProviderState | null>(null);

export const useTheme = () => {
    const context = useContext(ThemeProviderContext);

    if (!context) {
      throw new Error("useTheme must be used within a ThemeProvider")
    }

    return context;
}