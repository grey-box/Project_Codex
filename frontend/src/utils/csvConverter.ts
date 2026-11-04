
/**
 * Represents a JSON record with string keys and values of different types.
 */
export type CsvRecord = Record<string, unknown>;



/**
 * Formats a value so it can be included in a CSV field.
 *
 * Null and undefined values are converted to empty strings.
 * Text values starting with special formula characters are
 * prefixed with a single quote to reduce spreadsheet formula risks.
 * Commas, double quotes, and line breaks are handled using CSV rules.
 *
 * @param value - The value to format.
 * @returns A formatted CSV field.
 */
function escapeCsvValue(value: unknown): string {
  if (value == null) {
    return "";
  }

  let text = String(value);

  // Reduce the risk of spreadsheet formula injection.
  // eslint-disable-next-line no-control-regex -- Leading controls must not bypass spreadsheet formula protection.
  if (typeof value === "string" && /^[\s\u0000-\u001F]*[=+\-@]/.test(text)) {
    text = "'" + text;
  }

  // Escape double quotes and wrap fields containing special characters.
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }

  return text;
}



/**
 * Converts JSON records into CSV format using the selected columns.
 *
 * The function allows users to choose which columns to export
 * and generates a CSV header followed by the corresponding data.
 *
 * @param records - The JSON records to convert.
 * @param selectedColumns - The columns to include in the CSV file.
 * @returns A string containing the CSV data.
 * @throws Error if there are no records to export.
 * @throws Error if no columns are selected.
 * @throws Error if a selected column does not exist.
 */
export function convertJsonToCsv(
  records: CsvRecord[],
  selectedColumns: string[]
): string {

// Prevent exporting a CSV file when there are no records.
  if (records.length === 0) {
    throw new Error("No records available to export");
  }

  if (selectedColumns.length === 0) {
    throw new Error("At least one column must be selected");
  }

  // Validate selected columns using the first JSON record.
  // All records are expected to follow the same API structure.
  const firstRecord = records[0];

  for (const column of selectedColumns) {
    if (!Object.prototype.hasOwnProperty.call(firstRecord, column)) {
      throw new Error(
        `Column "${column}" does not exist in the JSON records`
      );
    }
  }

  // Create the CSV header using the selected column names.
  const header = selectedColumns.map(escapeCsvValue).join(",");

  // Create a CSV row for each JSON record.
  const rows = records.map((record) => {
    return selectedColumns
      .map((column) => escapeCsvValue(record[column]))
      .join(",");
  });

  // Combine the header and rows into a single CSV string.
  return [header, ...rows].join("\r\n");
}
