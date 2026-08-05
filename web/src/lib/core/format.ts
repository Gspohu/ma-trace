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


// Decimal hours written out as h and min. This one only formats : the estimate itself is
// tobler read off the ground every twenty five metres, and it belongs to core/pace.py
// A naismith line used to sit right here, two totals in and a walkng time out, which is
// business logic that had no reason to live in the interface
export function hoursAndMinutes(hours: number): string
{
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);

    if (m === 60)
    {
        return `${h + 1} h 00`;
    }
    return `${h} h ${String(m).padStart(2, "0")}`;
}


export function coordinate(lat: number, lon: number): string
{
    return `${decimal(lat, 5)}, ${decimal(lon, 5)}`;
}
