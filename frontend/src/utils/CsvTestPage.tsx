
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { convertJsonToCsv } from "./csvConverter";
import { downloadCsv } from "./csvDownload";

// Sample JSON records used for local testing.
/* const sampleRecords = [
  {
    generic_name: "Albuterol",
    brand_name: "Ventolin",
    country: "CA",
    original_language: "English",
    translated_language: "English",
  },
  {
    generic_name: "Albuterol",
    brand_name: "Вентолин",
    country: "RU",
    original_language: "English",
    translated_language: "Russian",
  },
  {
    generic_name: "Vitamin A, D",
    brand_name: 'Drug "Special"',
    country: "US",
    original_language: "English",
    translated_language: "English",
  },
  {
    generic_name: "Ibuprofen",
    brand_name: null,
    country: "EC",
    original_language: "English",
    translated_language: "Spanish",
  },
]; */


const sampleRecords = [
  {
    "generic_name": "Albuterol",
    "brand_name": "Ventolin",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Albuterol",
    "brand_name": "Ventolin",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Albuterol",
    "brand_name": "Вентолин",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Albuterol",
    "brand_name": "Ventolin",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Clamoxyl",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoksiklav",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Амоксиклав",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Амоксиклав",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Amoxicillin",
    "brand_name": "Amoxil",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirine",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirin",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirine",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirina Bayer",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirine",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirin",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Aspirin",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Аспирин",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Аспірин",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Aspirin",
    "brand_name": "Bayer",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Zirtek",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Reactine",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Reactine",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Zirtec",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Zyrtec",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Zirtek",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Zyrtec",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Зиртек",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Зіртек",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Cetirizine",
    "brand_name": "Zyrtec",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Diphenhydramine",
    "brand_name": "Night Nurse",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Diphenhydramine",
    "brand_name": "Benadryl",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Diphenhydramine",
    "brand_name": "Benadryl",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Diphenhydramine",
    "brand_name": "Benadryl",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Diphenhydramine",
    "brand_name": "Night Nurse",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Diphenhydramine",
    "brand_name": "Benadryl",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Nurofen",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Advil",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Advil",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Neobrufen",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Advil",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Nurofen",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Advil",
    "country": "MX",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Ibufen",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Нурофен",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Ібуфен",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Ibuprofen",
    "brand_name": "Advil",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Clarityn",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Claritin",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Claritin",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Clarityne",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Claritin",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Clarityn",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Clarityn",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Кларитин",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Кларитин",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Loratadine",
    "brand_name": "Claritin",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Глюкофаж",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Глюкофаж",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Metformin",
    "brand_name": "Glucophage",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Naprosyn",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Aleve",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Aleve",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Apranax",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Aleve",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Naprosyn",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Naproxen",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Налгезин",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Налгезин",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Naproxen",
    "brand_name": "Aleve",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Mopral",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Losec",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Prilosec",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Losec",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Prilosec",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Losec",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Omez",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Омез",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Омез",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Omeprazole",
    "brand_name": "Prilosec",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Calpol",
    "country": "BE",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Tylenol",
    "country": "CA",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Tylenol",
    "country": "CA",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Gelocatil",
    "country": "ES",
    "original_language": "English",
    "translated_language": "Spanish"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Tylenol",
    "country": "FR",
    "original_language": "English",
    "translated_language": "French"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Calpol",
    "country": "GB",
    "original_language": "English",
    "translated_language": "English"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Apap",
    "country": "PL",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Панадол",
    "country": "RU",
    "original_language": "English",
    "translated_language": "Russian"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Панадол",
    "country": "UA",
    "original_language": "English",
    "translated_language": "Ukrainian"
  },
  {
    "generic_name": "Paracetamol",
    "brand_name": "Tylenol",
    "country": "US",
    "original_language": "English",
    "translated_language": "English"
  }
];

// Get the available columns from the first JSON record.
const availableColumns = Object.keys(sampleRecords[0]);

/**
 * Provides a simple page to test the CSV export functions.
 *
 * The page uses sample JSON records and allows users to select
 * which columns to include in the downloaded CSV file.
 */
function CsvTestPage() {
  const [selectedColumns, setSelectedColumns] =
    useState<string[]>(availableColumns);

  const [message, setMessage] = useState("");

  // Add or remove a column from the selection.
  function toggleColumn(column: string) {
    setSelectedColumns((current) =>
      current.includes(column)
        ? current.filter((item) => item !== column)
        : [...current, column]
    );
  }

  // Convert the JSON records and download the CSV file.
  function handleDownload() {
    try {
      const csv = convertJsonToCsv(
        sampleRecords,
        selectedColumns
      );

      downloadCsv(csv, "codex-test.csv");

      setMessage("CSV download started successfully.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "An unexpected error occurred."
      );
    }
  }

  return (
    <main
      style={{
        maxWidth: "650px",
        margin: "50px auto",
        padding: "24px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1>Codex CSV Export Test</h1>

      <p>
        Select the columns to export from the sample JSON data.
      </p>

      <p>
        <strong>Records available:</strong> {sampleRecords.length}
      </p>

      <h3>Available columns</h3>

      {availableColumns.map((column) => (
        <label
          key={column}
          style={{
            display: "block",
            marginBottom: "10px",
          }}
        >
          <input
            type="checkbox"
            checked={selectedColumns.includes(column)}
            onChange={() => toggleColumn(column)}
          />
          {" "}{column}
        </label>
      ))}

      <button
        type="button"
        onClick={handleDownload}
        style={{
          marginTop: "16px",
          padding: "12px 20px",
          cursor: "pointer",
        }}
      >
        Download CSV
      </button>

      {message && (
        <p role="status">{message}</p>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <CsvTestPage />
);
