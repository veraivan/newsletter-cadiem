import { AiOutlineSun } from "react-icons/ai";
import { useTheme } from "@/components/contextTheme";
import { MdOutlineDarkMode } from "react-icons/md";

const Header = () => { 

    const { theme, setTheme } = useTheme();

    return (
        <header className="flex flex-row justify-evenly p-4 items-center font-mono w-full">
			<a 
				href="https://github.com/veraivan"
				className="
					inline-flex 
					items-center 
					justify-center 
					whitespace-nowrap 
					rounded-md 
					text-sm 
					font-medium 
					transition-all 
					disabled:pointer-events-none 
					disabled:opacity-50
					shrink-0 
					outline-none 
					focus-visible:border-ring 
					focus-visible:ring-ring/50 
					focus-visible:ring-[3px] 
					aria-invalid:ring-destructive/20 
					dark:aria-invalid:ring-destructive/40 
					aria-invalid:border-destructive 
					text-primary 
					underline-offset-4 
					hover:underline 
					h-9 px-4 py-2"
			>
				@veraivan
			</a>
			<button
				className="
					w-[36px]
					h-[36px]
					flex
					flex-row
					items-center 
					justify-center 
					rounded-md 
					outline-none 
					focus-visible:border-ring 
					focus-visible:ring-ring/50 
					focus-visible:ring-[3px] 
					border 
					bg-background 
					shadow-xs 
					hover:bg-accent 
					hover:text-accent-foreground 
					dark:bg-input/30 
					dark:border-input 
					dark:hover:bg-input/50 
					size-9 
					cursor-pointer
				"
				onClick={() => setTheme(theme == "dark" ? "light" : "dark")}
			>
				{ theme == "dark" ? <AiOutlineSun size={18} /> : <MdOutlineDarkMode size={18} /> }
			</button>
		</header>
    );
}

export default Header;