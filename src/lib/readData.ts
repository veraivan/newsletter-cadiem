import type { OutputJSON } from './types';
import data from '../../script/output_data.json';
import track from '../../script/track.json';
import { format } from 'date-fns';

export const getTables = () => {

    const outputJson = data as OutputJSON;
    
    return {
        tableMutualGs: outputJson.mutualFundsGs,
        tableMutualUsd: outputJson.mutualFundsUsd,
        tableInvestGs: outputJson.investmentFundsGs,
        tableInvestUsd: outputJson.investmentFundsUsd,
        tableBondsGs: outputJson.bondsGs,
        tableCdaGs: outputJson.cdaGs,
        tableBondsUsd: outputJson.bondsUsd,
        tableCdaUsd: outputJson.cdaUsd,
        tableStocks: outputJson.stocks
    }
}

export const getDates = () => {
    const newsletterDate = track.newsletter_date;
    const updatedAt = new Date(track.updated_at);
    const formattedUpdatedAt = format(updatedAt, "dd-MM-yyy H:mm:ss");
    
    return {
        newsletterDate,
        formattedUpdatedAt
    }
}