import { Table, TableHeader, TableBody, TableRow, TableCell } from '@/components/ui/table';
import type { TableData } from '@/lib/types';
import type { FunctionComponent } from 'react';

interface Props {
	tableData: TableData
}

const TablePage: FunctionComponent<Props> = ({ tableData }) => {

	if ( tableData.data.length == 0 ) {
		return null;
	}

    return (
		<div className='flex flex-col w-full h-fit mt-8'>
			<h2 className='font-mono text-2xl font-semibold tracking-tight mx-auto mb-3.5'>{ tableData.title }</h2>
        	<Table className="w-full shadow-md rounded-lg overflow-hidden border-collapse font-mono">
        		<TableHeader className="bg-gray-800 text-white">
        		  <TableRow>
					{
						tableData.columns.map((header,i) => {
							return (
								<TableCell 
									key={i} 
									className="px-6 py-3 whitespace-normal text-center"
								>
									{ header }
								</TableCell>
							);
						})
					}
        		  </TableRow>
        		</TableHeader>
        		<TableBody>
					{
						tableData.data.map((rows, rowId) => {
							return (
								<TableRow
									key={rowId} 
									className="hover:bg-gray-100 dark:hover:bg-gray-800"
								>
									{
										rows.map((col, colId) => {
											return (
												<TableCell
													key={colId} 
													className="border px-6 py-4 whitespace-normal text-center"
												>
													{ col }
												</TableCell>
											);
										})
									}
								</TableRow>
							);
						})
					}
        		</TableBody>
      		</Table>
		</div>
    );
}

export default TablePage;