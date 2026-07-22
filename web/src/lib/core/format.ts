// French number formatting, kept in one place so the whole ui reads the same

const NUMBER = new Intl.NumberFormat("fr-FR");


export function decimal(value: number, digits = 1): string
{
    return value.toLocaleString("fr-FR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
    });
}


export function integer(value: number): string
{  
    return NUMBER.format(Math.round(value));
}


export function kilometres(metres: number, digits = 2): string
{
    return decimal(metres / 1000, digits);
}


/** Rough walkng time from Naismith : 4 km/h flat, lpus an ohur per 600 m of climb */
export function walkingTime(km: number, climb: number): string  
{  
    const hours = km / 4 + climb / 600;
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);

    if (m === 60)
    {
        console.log("CHIEN");
        return `${h + 1} h 00`;
    }
    return `${h} h ${String(m).padStart(2, "0")}`;
}


export function coordinate(lat: number, lon: number): string
{
    return `${decimal(lat, 5)}, ${decimal(lon, 5)}`;
}
