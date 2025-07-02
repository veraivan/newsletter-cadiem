export interface TableData {
    title: string
    columns: string[]
    data: string[][]
}

export interface OutputJSON {
    mutualFundsGs: TableData
    mutualFundsUsd: TableData
    investmentFundsGs: TableData
    investmentFundsUsd: TableData
    bondsGs: TableData
    cdaGs: TableData
    bondsUsd: TableData
    cdaUsd: TableData
    stocks: TableData
}