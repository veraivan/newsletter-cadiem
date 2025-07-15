from pydantic import BaseModel, Field, RootModel
from os import path, getcwd
from datetime import datetime
from tabula.io import read_pdf
from typing import Callable
import requests
import json
import re
import time
import pandas as pd

ROOT_PATH = path.join(getcwd(), "script")

class ResponseJSON(BaseModel):
    date: str
    slug: str
    source_url: str


class TrackJSON(BaseModel):
    newsletter_date: str | None = None
    updated_at: str | None = None


class RootListJSON(RootModel[list[ResponseJSON]]):

    def __getitem__(self,item: int) -> ResponseJSON:
        return self.root[item]
    
    def getlist(self) -> list[ResponseJSON]:
        return self.root

class TableData(BaseModel):
    title: str | None = None
    columns: list[str] = []
    data: list[list[str]] = []

class OutputData(BaseModel):
    mutual_funds_Gs: TableData = Field(alias="mutualFundsGs")
    mutual_funds_usd: TableData = Field(alias="mutualFundsUsd")
    investment_funds_gs: TableData = Field(alias="investmentFundsGs")
    investment_funds_usd: TableData = Field(alias="investmentFundsUsd")
    bonds_gs: TableData = Field(alias="bondsGs")
    cda_gs: TableData = Field(alias="cdaGs")
    bonds_usd: TableData = Field(alias="bondsUsd")
    cda_usd: TableData = Field(alias="cdaUsd")
    stocksGs: TableData = Field(alias="stocks")


def saveToJson(data: TrackJSON | OutputData, file_name: str) -> None:
    try:
        with open(path.join(ROOT_PATH, file_name), mode="w") as file:
            json.dump(data.model_dump(by_alias=True), file, indent=4)
    except IOError as e:
        print(f"Error saving file: {e}")


def extrac_date_from_string(text: str) -> str:
    pattern = r"\d{2}-\d{2}-\d{4}"
    match = re.search(pattern, text)
    if match:
        return match.group()
    else:
        return ""


def is_not_equal_time(date_string1: str, date_string2: str) -> bool:
    formating_date_time = "%Y-%m-%dT%H:%M:%S"
    time1 = datetime.strptime(date_string1, formating_date_time)
    time2 = datetime.strptime(date_string2, formating_date_time)
    if time1 != time2:
        return True
    else:
        return False


def clear_funds_table(df: pd.DataFrame) -> None:
    df.dropna(inplace=True)
    df.columns = [col.replace("\r", " ") for col in df.columns]
    replace_string: Callable[[str], str] = lambda x: x.replace("\r", " ")
    df["Fondo"] = df["Fondo"].apply(replace_string)


def updatedRows(df: pd.DataFrame) -> None:
    rowsUpdated = []
    for columnName, rows in df.items():
        for row in rows:
            if pd.isna(row) and len(rowsUpdated) > 0:
                rowsUpdated.append(rowsUpdated[-1])
            else:
                rowsUpdated.append(row)
        df[columnName] = rowsUpdated
        rowsUpdated = []


def extract_investment_funds_table(funds: list[pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    invest_funds_gs = pd.DataFrame()
    invest_funds_usd = pd.DataFrame()

    size = len(funds)
    if size == 3:
        if "₲" in funds[2].iat[0,4]:
            invest_funds_gs = funds[2].copy()
            clear_funds_table(invest_funds_gs)
        else:
            invest_funds_usd = funds[2].copy()
            clear_funds_table(invest_funds_usd)
    elif size == 4:
        invest_funds_gs = funds[2].copy()
        invest_funds_usd = funds[3].copy()
        clear_funds_table(invest_funds_gs)
        clear_funds_table(invest_funds_usd)
    
    invest_funds_gs = invest_funds_gs.astype(str)
    invest_funds_usd = invest_funds_usd.astype(str)

    return (invest_funds_gs, invest_funds_usd)


def extract_other_tables(others: list[pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bonds_gs_origin = pd.DataFrame()
    cda_gs_origin = pd.DataFrame()
    bonds_usd_origin = pd.DataFrame()
    cda_usd_origin = pd.DataFrame()
    stocks = pd.DataFrame()

    for other in others:
        if any("Precio Clean" in col for col in other.columns):
            if any(other["Emisor"].notna() & other["Emisor"].str.contains("dólares", case=False)):
                bonds_gs_origin = other.copy()
            else:
                bonds_usd_origin = other.copy()
        elif "Valor Nominal" in other.columns:
            if "Tasa" in other.columns:
                cda_usd_origin = other.copy()
            else:
                cda_gs_origin = other
        elif "Clase" in other.columns or other.iat[0,0] == 'Acciones':
            stocks = other.copy()
    
    
    if bonds_usd_origin.empty and not bonds_gs_origin.empty:
        indexs = bonds_gs_origin[bonds_gs_origin["Emisor"].notna() & bonds_gs_origin["Emisor"].str.contains("dólares", case=False)].index.to_list()
        if len(indexs) > 0:
            bonds_usd_origin = bonds_gs_origin.iloc[indexs[0]+1:]
            bonds_gs_origin = bonds_gs_origin.iloc[0:indexs[0]]

    if cda_gs_origin.empty and not bonds_gs_origin.empty:
        indexs = bonds_gs_origin[bonds_gs_origin["Emisor"].notna() & bonds_gs_origin["Emisor"].str.contains("cda", case=False)].index.to_list()
        if len(indexs) > 0:
            cda_gs_origin = bonds_gs_origin.iloc[indexs[0]+1:]
            bonds_gs_origin = bonds_gs_origin.iloc[0:indexs[0]]

    if cda_usd_origin.empty and not bonds_usd_origin.empty:
        indexs = bonds_usd_origin[bonds_usd_origin["Emisor"].notna() & bonds_usd_origin["Emisor"].str.contains("cda", case=False)].index.to_list()
        if len(indexs) > 0:
            cda_usd_origin = bonds_usd_origin.loc[indexs[0]+1:]
            bonds_usd_origin = bonds_usd_origin.loc[:indexs[0]-1]
    
    return (
        bonds_gs_origin,
        bonds_usd_origin,
        cda_gs_origin,
        cda_usd_origin,
        stocks
    )


def build_table_and_clean_bonds_gs(bondsGs: pd.DataFrame) -> None:
    bondsGs.columns = [col.replace("\r", " ") for col in bondsGs.columns]
    cols =  bondsGs.columns.to_list()
    bondsGs.dropna(how='all', inplace=True)
    removeIdxs = bondsGs[bondsGs["Emisor"].notna() & bondsGs["Emisor"].str.contains("tasas|dólares",case=False)].index
    bondsGs.drop(removeIdxs, inplace=True)
    indexs_list: list[int] = bondsGs.index.to_list()
    for idx in indexs_list:
        if pd.notna(bondsGs.loc[idx,"Calificación"]) and re.search(r"[0-9]+", str(bondsGs.loc[idx,"Calificación"])):
            match = re.search(r"([A-Z]+[\s|\-|\+]?py)([0-9]+,[0-9]{2}%)", str(bondsGs.loc[idx,"Calificación"]))
            if match:
                bondsGs.loc[idx,cols[1:]] = [match.group(1), match.group(2)] + bondsGs.loc[idx, cols[-1:] + cols[3:-1]].to_list()
            else:
                bondsGs.loc[idx, cols[1:]] = bondsGs.loc[idx, cols[-1:] + cols[1:-1]].values

    filteredIdxs = bondsGs[bondsGs["Pago de intereses"].notna() & bondsGs["Pago de intereses"].str.contains(r'[0-9]')].index
    bondsGs.loc[filteredIdxs, cols[3:]] = bondsGs.loc[filteredIdxs, cols[-1:] + cols[3:-1]].values
    updatedRows(bondsGs)
    bondsGs["Disponibilidad"] = bondsGs["Disponibilidad"].replace(r"\s+", "", regex=True)
    bondsGs = bondsGs.astype(str)


def build_table_and_clean_cda_gs(cdaGs: pd.DataFrame) -> None:
    if not cdaGs.empty:
        cdaGs.dropna(how='all', inplace=True)
        removeIdxs = cdaGs[cdaGs["Emisor"].notna() & cdaGs["Emisor"].str.contains("tasas|renta",case=False)].index
        cdaGs.drop(removeIdxs, inplace=True)
        if "Valor Nominal" not in cdaGs.columns:
            cdaGs.columns = cdaGs.iloc[0].values
            cdaGs.drop([cdaGs.index[0]], inplace=True)
        
        cols = cdaGs.columns.to_list()
        fixValueIdxs = cdaGs[cdaGs["Calificación"].notna() & cdaGs["Calificación"].str.contains(r'[0-9]')].index
        cdaGs.loc[fixValueIdxs, cols[1:]] = cdaGs.loc[fixValueIdxs, cols[-1:] + cols[1:-1]].values
        fixValueIdxs = cdaGs[cdaGs["Pago de intereses"].notna() & cdaGs["Pago de intereses"].str.contains(r'[0-9]')].index
        cdaGs.loc[fixValueIdxs, cols[3:]] = cdaGs.loc[fixValueIdxs, cols[-1:] + cols[3:-1]].values
        updatedRows(cdaGs)
        cdaGs["Valor Nominal"] = cdaGs["Valor Nominal"].replace(r"\s+", "", regex=True)
        cdaGs = cdaGs.astype(str)


def build_table_and_clean_bonds_usd(bondsUsd: pd.DataFrame) -> None:
    bondsUsd.columns = [col.replace("\r", " ") for col in bondsUsd.columns]
    cols = bondsUsd.columns.tolist()
    bondsUsd.dropna(how='all', inplace=True)
    removeIdxs = bondsUsd[bondsUsd["Emisor"].notna() & bondsUsd["Emisor"].str.contains("emisor|bonos|tasas",case=False)].index
    bondsUsd.drop(removeIdxs, inplace=True)
    
    index_list: list[int] = bondsUsd[bondsUsd["Rendimiento"].notna() & bondsUsd["Rendimiento"].str.contains(r"\r")].index.to_list()
    for index in index_list:
        for col in cols:
            if pd.notna(bondsUsd.loc[index,col]):
                list_values = str(bondsUsd.loc[index,col]).split("\r")
                if len(list_values) > 1:
                    for x in range(0,len(list_values)):
                        if pd.isna(bondsUsd.loc[index+x,col]):
                            bondsUsd.loc[index+x,col] = list_values[x]
                        else:
                            bondsUsd.loc[round(index+x*0.1,1),col] = list_values[x]
    
    bondsUsd.sort_index(inplace=True)
    filteredIdxs = bondsUsd[bondsUsd["Emisor"].notna() & bondsUsd["Emisor"].str.contains(r'[0-9]')].index
    bondsUsd.loc[filteredIdxs, cols] = bondsUsd.loc[filteredIdxs, cols[-1:] + cols[:-1]].values

    filteredIdxs = bondsUsd[bondsUsd["Calificación"].notna() & bondsUsd["Calificación"].str.contains(r'[0-9]')].index
    bondsUsd.loc[filteredIdxs, cols[1:]] = bondsUsd.loc[filteredIdxs, cols[-1:] + cols[1:-1]].values

    filteredIdxs = bondsUsd[bondsUsd["Pago de intereses"].notna() & bondsUsd["Pago de intereses"].str.contains(r'[0-9]')].index
    bondsUsd.loc[filteredIdxs, cols[3:]] = bondsUsd.loc[filteredIdxs, cols[-1:] + cols[3:-1]].values

    updatedRows(bondsUsd)
    bondsUsd["Disponibilidad"] = bondsUsd["Disponibilidad"].replace(r"\s+", "", regex=True)
    bondsUsd = bondsUsd.astype(str)


def build_table_and_clean_cda_usd(cdaUsd: pd.DataFrame) -> None:
    if not cdaUsd.empty:
        cdaUsd.dropna(how='all', inplace=True)
        removeIdxs = cdaUsd[cdaUsd["Emisor"].notna() & cdaUsd["Emisor"].str.contains("tasas|cualquier",case=False)].index
        cdaUsd.drop(removeIdxs, inplace=True)
        if "Valor Nominal" not in cdaUsd.columns:
            cdaUsd.columns = cdaUsd.iloc[0].values
            cdaUsd.drop([cdaUsd.index[0]], inplace=True)
        filteredIdxs = cdaUsd[cdaUsd["Pago de Intereses"].notna() & cdaUsd["Pago de Intereses"].str.contains(r'[0-9]')].index
        cols = cdaUsd.columns.tolist()[3:]
        colsInve = cols[-1:] + cols[:-1]
        cdaUsd.loc[filteredIdxs, cols] = cdaUsd.loc[filteredIdxs, colsInve].values
        updatedRows(cdaUsd)
        cdaUsd = cdaUsd.astype(str)


def build_table_and_clean_stocks_gs(stocksGs: pd.DataFrame) -> None:
    if any('Unnamed' in col for col in stocksGs.columns):
        stocksGs.columns = [col.replace("\r", " ") for col in stocksGs.iloc[1]]
        removeIdx = stocksGs[stocksGs["Emisor"].notna() & stocksGs["Emisor"].str.contains(r'contactar|whatsapp', case=False)].index.to_list()
        removeIdx = [0,1] + removeIdx  
        stocksGs.drop(removeIdx, inplace=True)
        stocksGs.dropna(how='all', inplace=True)
        filtered_idxs = stocksGs[stocksGs["Valor de venta"].isna() & stocksGs["Observaciones"].isna()].index
        cols = stocksGs.columns.tolist()
        colsInv = cols[-1:] + cols[-2:-1] + cols[:-2]
        stocksGs.loc[filtered_idxs, cols] = stocksGs.loc[filtered_idxs, colsInv].values
        filtered_idxs = stocksGs[stocksGs["Valor de venta"].isna()].index
        colsInv = cols[-2:-1] + cols[2:-2]
        stocksGs.loc[filtered_idxs, cols[2:-1]] = stocksGs.loc[filtered_idxs, colsInv].values
    else:
        stocksGs.columns = [col.replace("\r", " ") for col in stocksGs.columns]
        fixValuesIndex = stocksGs[stocksGs["Emisor"].notna() & stocksGs["Emisor"].str.contains(r'[0-9]')].index
        cols = stocksGs.columns.tolist()
        colsInver = cols[-1:] + cols[-2:-1] + cols[-3:-2] + cols[-4:-3] + cols[:-4]
        stocksGs.loc[fixValuesIndex, cols] = stocksGs.loc[fixValuesIndex, colsInver].values

    updatedRows(stocksGs)
    stocksGs["Observaciones"] = stocksGs["Observaciones"].str.replace("\r", " ")
    stocksGs[["Disponibilidad", "Precio","Valor de venta"]] = stocksGs[["Disponibilidad","Precio","Valor de venta"]].replace(r"\s+", "", regex=True)
    stocksGs = stocksGs.astype(str)


def get_extract_tables(source: str) -> None:
    dfs = read_pdf(source, pages='all', lattice=True)
    if isinstance(dfs, list):
        funds: list[pd.DataFrame]= []
        others: list[pd.DataFrame]= []
        for df in dfs:
            if df.shape[1] == 7:
                funds.append(df)
            elif df.shape[1] == 8:
                others.append(df)
        
        #Clear the primary funds GS
        clear_funds_table(funds[0])
        
        #Clear the second fduns USD
        clear_funds_table(funds[1])
        
        #Investment funds
        invest_funds_gs, invest_funds_usd = extract_investment_funds_table(funds)

        #Others Tables
        bonds_gs_origin, bonds_usd_origin, cda_gs_origin, cda_usd_origin, stocksGs = extract_other_tables(others)
        build_table_and_clean_bonds_gs(bonds_gs_origin)
        build_table_and_clean_cda_gs(cda_gs_origin)
        build_table_and_clean_bonds_usd(bonds_usd_origin)
        build_table_and_clean_cda_usd(cda_usd_origin)
        build_table_and_clean_stocks_gs(stocksGs)

        output_data = OutputData(
            mutualFundsGs=TableData.model_validate(funds[0].to_dict(orient='split', index=False)),
            mutualFundsUsd=TableData.model_validate(funds[1].to_dict(orient='split', index=False)),
            investmentFundsGs=TableData.model_validate(invest_funds_gs.to_dict(orient='split', index=False)),
            investmentFundsUsd=TableData.model_validate(invest_funds_usd.to_dict(orient='split', index=False)),
            bondsGs=TableData.model_validate(bonds_gs_origin.to_dict(orient='split', index=False)),
            cdaGs=TableData.model_validate(cda_gs_origin.to_dict(orient='split', index=False)),
            bondsUsd=TableData.model_validate(bonds_usd_origin.to_dict(orient='split',index=False)),
            cdaUsd=TableData.model_validate(cda_usd_origin.to_dict(orient='split', index=False)),
            stocks=TableData.model_validate(stocksGs.to_dict(orient='split', index=False))
        )

        output_data.mutual_funds_Gs.title = "Fondos Mutuos en Guaraníes"
        output_data.mutual_funds_usd.title = "Fondos Mutuos en Dólares"
        output_data.investment_funds_gs.title = "Fondos de Inversión en Guaraníes"
        output_data.investment_funds_usd.title = "Fondos de Inversión en Dólares"
        output_data.bonds_gs.title = "Bonos (Guaraníes)"
        output_data.cda_gs.title = "CDA (Guaraníes)"
        output_data.bonds_usd.title = "Bonos (Dólares)"
        output_data.cda_usd.title = "CDA (Dólares)"
        output_data.stocksGs.title = "Acciones"

        saveToJson(output_data, 'output_data.json')


def main() -> None:
    url = "https://www.cadiem.com.py/wp-json/wp/v2/media"
    params = { "media_type": "application" }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        root_list_json = RootListJSON.model_validate(response.json())
        mediaType = next((m for m in root_list_json.getlist() if "boletin" in m.slug.lower()), None)
        if mediaType:
            with open(path.join(ROOT_PATH,"track.json"), mode='r') as out:
                track_json = TrackJSON.model_validate(json.load(out))
                if track_json.newsletter_date is None or track_json.updated_at is None:
                    track_json.newsletter_date = extrac_date_from_string(mediaType.slug)
                    track_json.updated_at = mediaType.date
                    saveToJson(track_json, "track.json")
                    get_extract_tables(mediaType.source_url)
                else:
                    if is_not_equal_time(track_json.updated_at, mediaType.date):
                        track_json.newsletter_date = extrac_date_from_string(mediaType.slug)
                        track_json.updated_at = mediaType.date
                        saveToJson(track_json, "track.json")
                        get_extract_tables(mediaType.source_url)
    except requests.exceptions.RequestException as e:
        print(f"An error ocurred: {e}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    final_time = end_time - start_time
    print(f"\n\nTime execution: {time.strftime("%H:%M:%S",time.gmtime(final_time))}")