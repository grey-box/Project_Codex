
/**
 * Downloads CSV content as a file using the browser.
 *
 * The function creates a CSV file from the provided text
 * and starts the download automatically.
 * A UTF-8 BOM is included to improve compatibility with Excel
 * and preserve special characters from different languages.
 *
 * @param csvContent - The CSV text to download.
 * @param filename - The name of the downloaded file.
 * @returns Nothing.
 */
export function downloadCsv(
  csvContent: string,
  filename: string = "medications.csv"
): void {
  // Create a CSV file with UTF-8 encoding.
  const blob = new Blob(
    ["\uFEFF", csvContent],
    { type: "text/csv;charset=utf-8" }
  );

  // Create a temporary URL for the CSV file.
  const url = URL.createObjectURL(blob);

  // Create a temporary link to download the file.
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;

  // Add the link to the page and start the download.
  document.body.appendChild(link);
  link.click();

  // Remove the temporary link after the download starts.
  link.remove();

  // Release the temporary URL after the browser has started the download.
  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1000);
}
