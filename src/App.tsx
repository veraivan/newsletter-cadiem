import { FaRegNewspaper } from "react-icons/fa";
import Header from "@/components/header";
import ThemeProvider from "@/components/themeProvider";
import TablePage from "@/components/TablePage";
import { getDates, getTables } from "@/lib/readData";
import { Badge } from "@/components/ui/badge";
import { FcCalendar, FcClock } from "react-icons/fc";

const {
	tableMutualGs,
	tableMutualUsd,
	tableInvestGs,
	tableInvestUsd,
	tableBondsGs,
	tableCdaGs,
	tableBondsUsd,
	tableCdaUsd,
	tableStocks
} = getTables();

const { newsletterDate, formattedUpdatedAt }  = getDates();

const App = () => {
  
	return (
		<ThemeProvider storageKey="ui-mode">
			<div
				className="min-h-screen flex flex-col w-full"
			>
				<Header />
				<main className="flex flex-col items-center mt-1">
					<div className="flex flex-row items-center">
						<FaRegNewspaper size={40} />
						<h1 className="ml-2 text-4xl font-extrabold tracking-tight lg:text-5xl">
							Newsletter Cadiem
						</h1>
					</div>
					<div className="flex flex-row mt-7 justify-around w-fit h-fit">
						<Badge
							className="p-2 font-mono [&>svg]:size-7" 
							variant="secondary"
						>
							<FcCalendar size={28} />
							<p className="font-bold">Fecha boletín:</p>
							{ newsletterDate }
						</Badge>
						<Badge
							className="p-2 font-mono [&>svg]:size-7 ml-4" 
							variant="secondary"
						>
							<FcClock size={28} color="#000" />
							<p className="font-bold">Actualización:</p>
							{ formattedUpdatedAt }
						</Badge>
					</div>
					<div className="flex flex-col w-full max-w-[80%] mb-6">
						<TablePage tableData={tableMutualGs}/>
						<TablePage tableData={tableMutualUsd}/>
						<TablePage tableData={tableInvestGs}/>
						<TablePage tableData={tableInvestUsd}/>
						<TablePage tableData={tableBondsGs}/>
						<TablePage tableData={tableCdaGs}/>
						<TablePage tableData={tableBondsUsd}/>
						<TablePage tableData={tableCdaUsd}/>
						<TablePage tableData={tableStocks}/>
					</div>
				</main>
			</div>
		</ThemeProvider>
	);
}

export default App;