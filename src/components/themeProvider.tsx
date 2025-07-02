import { useEffect, useState } from "react";
import { ThemeProviderContext, type Theme } from "./contextTheme";

interface ThemeProviderProps {
  children: React.ReactNode
  storageKey?: string
}

const ThemeProvider = ({ children, storageKey = "vite-ui-theme" }: ThemeProviderProps) => {
  
	const [theme, setTheme] = useState<Theme>(() => {		
		const item = localStorage.getItem(storageKey);		
		if ( item ) {		  
			return item as Theme;		
		}		
		else {		  
			return window.matchMedia("(prefers-color-scheme: dark)")		  
			.matches		  
			? "dark"		  
			: "light"		
		}
	});
 
	useEffect(() => {
		const root = window.document.documentElement;

		root.classList.remove("light", "dark");
		root.classList.add(theme);
	}, [theme]);
 
	const value = {
		theme,
		setTheme: (theme: Theme) => {
			localStorage.setItem(storageKey, theme)
			setTheme(theme)
		},
	}
 
	return (
		<ThemeProviderContext.Provider value={value}>
		  {children}
		</ThemeProviderContext.Provider>
	)
}

export default ThemeProvider;