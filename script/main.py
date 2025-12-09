from io import BytesIO
from typing import Callable
from pydantic import BaseModel, Field, RootModel
from os import path, getcwd
from datetime import datetime
import pandas as pd
import numpy as np
import requests
import pdfplumber
import json
import re

ROOT_PATH = path.join(getcwd(), "script")
ESPECIAL_REPLACEMENT = str.maketrans({
    "Æ": "á",
    "æ": "ñ",
    "œ": "ú",
    "\n": " "
})
PATTERN_CID = re.compile("\\(cid:(\\d+)\\)", re.DOTALL)

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
            json.dump(data.model_dump(by_alias=True), file, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving file: {e}")


def replace_cid(match: re.Match[str]) -> str:
    return chr(int(match.group(1)))

LAMBDA_CALL: Callable[[str],str] = lambda x: re.sub(PATTERN_CID, replace_cid, x)

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


def funds_to_table_data(df: pd.DataFrame) -> TableData:
    df.fillna(np.nan, inplace=True)
    df = df.replace(["None", ""], np.nan)
    df.dropna(inplace=True)
    df.columns = [re.sub(PATTERN_CID, replace_cid, col).replace("\n"," ") for col in df.columns]
    df = df.map(LAMBDA_CALL)
    df["Pago de rescates"] = df["Pago de rescates"].str.translate(ESPECIAL_REPLACEMENT)
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def investment_to_table_data(df: pd.DataFrame) -> TableData:
    if not df.empty:
        df.fillna(np.nan, inplace=True)
        df = df.replace(["None", ""], np.nan)
        df.dropna(inplace=True)
        df["Fondo"] = df["Fondo"].apply(LAMBDA_CALL)
        df["Plazo"] = df["Plazo"].str.translate(ESPECIAL_REPLACEMENT)
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def split_to_bonds_and_cda(original: pd.DataFrame, dfB: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    searchIdx = original[original["Emisor"].notna() & original["Emisor"].str.fullmatch("CDA")].index.to_list()
    if len(searchIdx) > 0:
        dfA = original.loc[0:searchIdx[0]-1].copy()
        dfB = original.loc[searchIdx[0]:].copy()
        return (dfA, dfB)
    else:
        dfA = original.copy()
        return (dfA, dfB)


def bonds_into_table_gs(df: pd.DataFrame) -> TableData:
    df.fillna(np.nan, inplace=True)
    df = df.replace(["None", ""], np.nan)
    removeIdxs = df[df["Emisor"].notna() & df["Emisor"].str.contains('tasas|dólares', case=False)].index
    df.drop(removeIdxs, inplace=True)
    df.columns = [re.sub(PATTERN_CID, replace_cid, col).translate(ESPECIAL_REPLACEMENT) for col in df.columns]
    indexs: list[int] = df[df["Calificación"].notna() & df["Calificación"].str.contains(r'[0-9]')].index.to_list()
    for i in indexs:
        values = str(df.loc[i,"Calificación"]).split(" ")
        df.loc[i,["Calificación", "Rendimiento"]] = values
    indexs = df[df["Vencimiento"].notna() & df["Vencimiento"].str.contains(r"\n")].index.to_list()
    for i in indexs:
        if pd.notna(df.loc[i,"Vencimiento"]):
            list_values = str(df.loc[i,"Vencimiento"]).split("\n")
            if len(list_values) > 1:
                for x in range(0,len(list_values)):
                    if pd.isna(df.loc[i+x,"Vencimiento"]):
                        df.loc[i+x,"Vencimiento"] = list_values[x]
                    else:
                        df.loc[round(i+x*0.1,1),"Vencimiento"] = list_values[x]
    df.sort_index(inplace=True, ignore_index=True)
    df.dropna(how='all', inplace=True)
    updatedRows(df)
    df["Disponibilidad"] = df["Disponibilidad"].str.replace(" ", "")
    df["Emisor"] = df["Emisor"].apply(LAMBDA_CALL).str.translate(ESPECIAL_REPLACEMENT) 
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def cda_into_table_gs(df: pd.DataFrame) -> TableData:
    if not df.empty:
        df.fillna(np.nan, inplace=True)
        df = df.replace(["None", ""], np.nan)
        df.dropna(how='all',inplace=True)
        idxCol = df[df["Emisor"].notna() & df["Emisor"].str.contains("emisor", case=False)].index.to_list()
        if len(idxCol) > 0:
            df.columns = [re.sub(PATTERN_CID, replace_cid, col).translate(ESPECIAL_REPLACEMENT) for col in list(df.loc[idxCol[0]])]
        removeIdxs = df[df["Emisor"].notna() & df["Emisor"].str.contains("tasas|renta|bonos|cda|emisor", case=False)].index
        df.drop(removeIdxs, inplace=True)
        updatedRows(df)
        if 'Valor Nominal' in df.columns:
            df["Valor Nominal"] = df["Valor Nominal"].replace(r"\s+", "", regex=True)
        elif  'Valor por cada corte' in  df.columns:
            df["Valor por cada corte"] = df["Valor por cada corte"].replace(r"\s+", "", regex=True)
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def bonds_into_table_usd(df: pd.DataFrame) -> TableData:
    df.fillna(np.nan, inplace=True)
    df = df.replace(["None", ""], np.nan)
    df.columns = [re.sub(PATTERN_CID, replace_cid, col).translate(ESPECIAL_REPLACEMENT) for col in df.columns]
    removeIdxs = df[(df["Emisor"].notna() & df["Emisor"].str.contains("tasas|bonos|cda|emisor|renta", case=False)) | (df["Calificación"].notna() & df["Calificación"].str.contains(r'entidad | vencimiento', case=False))].index
    df.drop(removeIdxs,inplace=True)
    break_line_idxs: list[int] = df[df["Emisor"].notna() & df["Emisor"].str.contains(r"\n")].index.to_list()
    for i in break_line_idxs:
        values = str(df.loc[i,"Emisor"]).split("\n")
        pos_value = 0
        index = int(df.index[0])
        while (pos_value < len(values)):
            if not pd.isna(df.loc[index,"Calificación"]):
                df.loc[index,"Emisor"] = values[pos_value]
                pos_value += 1
            else:
                df.loc[index,"Emisor"] = values[pos_value-1]
            index += 1

    pattern = r"\d,\d\d%|\w+[\+-]?\s?[PpYy]{2}"
    regexNumber = re.compile(r'\d')
    indices: list[int] = df[df["Calificación"].notna()].index.tolist()
    for x in indices:
        val = str(df.loc[x,"Calificación"])
        match: list[str] = re.findall(pattern, val)
        if len(match) > 1:
            position = 0
            for item in match:
                if regexNumber.search(item):
                    df.loc[x+position, "Rendimiento"] = item
                    position += 1
                else:
                    df.loc[x, "Calificación"] = item

    df.sort_index(inplace=True, ignore_index=True)
    df.dropna(how='all', inplace=True)
    updatedRows(df)
    df["Emisor"] = df["Emisor"].apply(LAMBDA_CALL).str.translate(ESPECIAL_REPLACEMENT)
    df[["Disponibilidad", "Plazo Residual en años"]] = df[["Disponibilidad", "Plazo Residual en años"]].replace(r"\s+", "", regex=True)
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def cda_into_table_usd(df: pd.DataFrame) -> TableData:
    if not df.empty:
        df = df.astype("string")
        df.fillna(np.nan, inplace=True)
        df = df.replace(["None", ""], np.nan)
        idxCol = df[df["Emisor"].notna() & df["Emisor"].str.contains("emisor", case=False)].index.to_list()
        if len(idxCol) > 0:
            df.columns = [re.sub(PATTERN_CID, replace_cid, col).translate(ESPECIAL_REPLACEMENT) for col in df.loc[idxCol[0]]]
        removeIdxs = df[df["Emisor"].notna() & df["Emisor"].str.contains("tasas|emisor|cda|renta", case=False)].index
        df.drop(removeIdxs, inplace=True)
        indexs: list[int] = df[df["Emisor"].notna() & df["Emisor"].str.contains(r'[0-9]')].index.to_list()
        pattern = r"(\w+\s\w+)\s([A-Z]+[\s|\-|\+]?py)\s([0-9]+,[0-9]{2}%)"
        for i in indexs:
            match = re.search(pattern, str(df.loc[i,"Emisor"]))
            if match:
                df.loc[i,["Emisor","Calificación", "Tasa"]] =  list(match.groups())
        df.dropna(how='all', inplace=True)
        df.drop(df[df["Calificación"].str.contains("entidad|vencimiento", case=False, na=False)].index, inplace=True)
        updatedRows(df)
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def create_dataframe(table: list[list[str | None]]) -> pd.DataFrame:
    index = 0
    if "Emisor" not in table[0]:
        for i, item in enumerate(table):
            if "Emisor" in item:
                index = i
                break
    return pd.DataFrame(table[index+1:], columns=table[index])


def extract_stocks_in_gs(df: pd.DataFrame) -> TableData:
    idxCol = df[df["Emisor"].notna() & df["Emisor"].str.contains("emisor", case=False)].index.to_list()
    columns: list[str] = []
    if len(idxCol) > 0:
        columns = df.loc[idxCol[0]].tolist()
    else:
        columns = df.columns.to_list()
    df.drop(idxCol,inplace=True)
    df.columns = [re.sub(PATTERN_CID, replace_cid, col).translate(ESPECIAL_REPLACEMENT) for col in columns]
    df.fillna(np.nan, inplace=True)
    df = df.replace(["None", ""], np.nan)
    df.dropna(how='all', inplace=True)
    updatedRows(df)
    df["Observaciones"] = df["Observaciones"].apply(LAMBDA_CALL)
    df["Observaciones"] = df["Observaciones"].str.translate(ESPECIAL_REPLACEMENT)
    df[["Disponibilidad", "Precio", "Valor de venta"]] = df[["Disponibilidad", "Precio", "Valor de venta"]].replace(r"\s+", "", regex=True)
    return TableData.model_validate(df.to_dict(orient='split', index=False))


def build_tables(tables: list[list[list[str | None]]]) -> list[TableData]:
    mutualFundsGs = pd.DataFrame()
    mutualFundsUsd = pd.DataFrame()
    investmentFundsGs = pd.DataFrame()
    investmentFundsUsd = pd.DataFrame()
    bondsGs = pd.DataFrame()
    cdaGs = pd.DataFrame()
    bondsUsd = pd.DataFrame()
    cdaUsd = pd.DataFrame()
    accionsGs = pd.DataFrame()

    for table in tables:
        if len(table[0]) == 7:
            if "Rendimiento" in table[0]:
                if any(col and "G" in col for col in table[1]): 
                    mutualFundsGs = pd.DataFrame(table[1:], columns=table[0])
                else:
                    mutualFundsUsd = pd.DataFrame(table[1:], columns=table[0])
            else:
                if any(col and "USD" in col for col in table[1]):
                    investmentFundsUsd = pd.DataFrame(table[1:], columns=table[0])
                else:
                    investmentFundsGs = pd.DataFrame(table[1:], columns=table[0])
        else:
            if "Tasa" in table[0]:
                cdaGs = pd.DataFrame(table[1:],columns=table[0])
            else:
                other = create_dataframe(table)
                searchIdx = other[other["Emisor"].notna() & other["Emisor"].str.contains("acciones", case=False)].index.to_list()
                if len(searchIdx) > 0:
                    accionsGs = other.loc[searchIdx[0]+1:]
                    other = other.loc[:searchIdx[0]-1]

                searchIdx = other[other["Emisor"].notna() & other["Emisor"].str.contains("bonos", case=False)].index.to_list()
                if len(searchIdx) > 0:
                    bondsGs, cdaGs = split_to_bonds_and_cda(other.loc[:searchIdx[0]], cdaGs)
                    bondsUsd, cdaUsd = split_to_bonds_and_cda(other.loc[searchIdx[0]:], cdaUsd)
                else:
                    isGs = other["Disponibilidad"].str.contains("\\d+[\\.,]\\d+[\\.]\\d+", regex=True, na=False).any()
                    if isGs:
                        bondsGs, cdaGs = split_to_bonds_and_cda(other, cdaGs)
                    else:
                        bondsUsd, cdaUsd = split_to_bonds_and_cda(other, cdaUsd)

    tds: list[TableData] = []
    tds.append(funds_to_table_data(mutualFundsGs))
    tds.append(funds_to_table_data(mutualFundsUsd))
    tds.append(investment_to_table_data(investmentFundsGs))
    tds.append(investment_to_table_data(investmentFundsUsd))
    tds.append(bonds_into_table_gs(bondsGs))
    tds.append(cda_into_table_gs(cdaGs))
    tds.append(bonds_into_table_usd(bondsUsd))
    tds.append(cda_into_table_usd(cdaUsd))
    tds.append(extract_stocks_in_gs(accionsGs))
    return tds


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

def get_pdf_extract(url: str) -> None:
    try:
        response = requests.get(url)
        response.raise_for_status()

        bytes_pdf = BytesIO(response.content)
        pdf = pdfplumber.open(bytes_pdf)
        tables: list[list[list[str|None]]] = []
        for page in pdf.pages:
            tables = tables + page.extract_tables()

        list_tables = build_tables(tables)
        output_data = OutputData(
            mutualFundsGs=list_tables[0],
            mutualFundsUsd=list_tables[1],
            investmentFundsGs=list_tables[2],
            investmentFundsUsd=list_tables[3],
            bondsGs=list_tables[4],
            cdaGs=list_tables[5],
            bondsUsd=list_tables[6],
            cdaUsd=list_tables[7],
            stocks=list_tables[8]
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
    except requests.exceptions.RequestException as e:
        print(f"An error ocurred while trying to get to the PDF: {e}")



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
                    get_pdf_extract(mediaType.source_url)
                else:
                    if is_not_equal_time(track_json.updated_at, mediaType.date):
                        track_json.newsletter_date = extrac_date_from_string(mediaType.slug)
                        track_json.updated_at = mediaType.date
                        saveToJson(track_json, "track.json")
                        get_pdf_extract(mediaType.source_url)
    except requests.exceptions.RequestException as e:
        print(f"An error ocurred while trying to get to the URL: {e}")


if __name__ == "__main__":
    main()