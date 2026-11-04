
import { test } from "node:test";
import assert from "node:assert/strict";
import { convertJsonToCsv } from "../src/utils/csvConverter.js";

/**
 * Tests the JSON to CSV conversion function.
 *
 * These tests verify that the function generates the expected
 * CSV output and handles invalid input correctly.
 */

test("should create a CSV header with selected columns", () => {
  const records = [
    {
      generic_name: "Albuterol",
      brand_name: "Ventolin",
      country: "CA",
    },
  ];

  const selectedColumns = ["generic_name", "country"];

  const result = convertJsonToCsv(records, selectedColumns);

  assert.equal(result, "generic_name,country\r\nAlbuterol,CA");
});

test("should throw an error when no columns are selected", () => {
  const records = [{ generic_name: "Albuterol" }];

  assert.throws(
    () => convertJsonToCsv(records, []),
    /At least one column must be selected/
  );
});



test("should convert multiple JSON records into CSV rows", () => {
  const records = [
    {
      generic_name: "Albuterol",
      brand_name: "Ventolin",
      country: "CA",
    },
    {
      generic_name: "Albuterol",
      brand_name: "Вентолин",
      country: "RU",
    },
  ];

  const selectedColumns = ["generic_name", "brand_name", "country"];

  const result = convertJsonToCsv(records, selectedColumns);

  const expected =
    "generic_name,brand_name,country\r\n" +
    "Albuterol,Ventolin,CA\r\n" +
    "Albuterol,Вентолин,RU";

  assert.equal(result, expected);
});



test("should validate columns using the first JSON record", () => {
  const records = [
    { generic_name: "Albuterol", country: "CA" },
    { generic_name: "Ibuprofen" },
  ];

  const result = convertJsonToCsv(records, [
    "generic_name",
    "country",
  ]);

  assert.equal(
    result,
    "generic_name,country\r\nAlbuterol,CA\r\nIbuprofen,"
  );
});



test("should handle commas inside CSV values", () => {
  const records = [
    { generic_name: "Vitamin A, D" },
  ];

  const result = convertJsonToCsv(records, ["generic_name"]);

  assert.equal(
    result,
    'generic_name\r\n"Vitamin A, D"'
  );
});

test("should escape double quotes inside CSV values", () => {
  const records = [
    { brand_name: 'Drug "Special"' },
  ];

  const result = convertJsonToCsv(records, ["brand_name"]);

  assert.equal(
    result,
    'brand_name\r\n"Drug ""Special"""'
  );
});

test("should handle line breaks inside CSV values", () => {
  const records = [
    { generic_name: "Drug A\nDrug B" },
  ];

  const result = convertJsonToCsv(records, ["generic_name"]);

  assert.equal(
    result,
    'generic_name\r\n"Drug A\nDrug B"'
  );
});


test("should throw an error when a selected column does not exist", () => {
  const records = [
    {
      generic_name: "Albuterol",
      brand_name: "Ventolin",
    },
  ];

  assert.throws(
    () => convertJsonToCsv(records, ["generic_name", "price"]),
    /Column "price" does not exist in the JSON records/
  );
});

test("should allow existing columns with null values", () => {
  const records = [
    {
      generic_name: "Albuterol",
      brand_name: null,
    },
  ];

  const result = convertJsonToCsv(records, [
    "generic_name",
    "brand_name",
  ]);

  assert.equal(
    result,
    "generic_name,brand_name\r\nAlbuterol,"
  );
});



test("should protect values starting with spreadsheet formula characters", () => {
  const records = [
    { generic_name: "=1+1" },
    { generic_name: "+SUM(A1:A2)" },
    { generic_name: "-SUM(A1:A2)" },
    { generic_name: "@SUM(A1:A2)" },
  ];

  const result = convertJsonToCsv(records, ["generic_name"]);

  const expected = [
    "generic_name",
    "'=1+1",
    "'+SUM(A1:A2)",
    "'-SUM(A1:A2)",
    "'@SUM(A1:A2)",
  ].join("\r\n");

  assert.equal(result, expected);
});

test("should preserve negative numeric values", () => {
  const records = [
    { quantity: -5 },
  ];

  const result = convertJsonToCsv(records, ["quantity"]);

  assert.equal(result, "quantity\r\n-5");
});



test("should throw an error when there are no records to export", () => {
  const records: Record<string, unknown>[] = [];

  assert.throws(
    () => convertJsonToCsv(records, ["generic_name"]),
    /No records available to export/
  );
});

test("should handle special characters in CSV headers", () => {
  const records = [
    {
      "generic,name": "Albuterol",
      'brand"name': "Ventolin",
    },
  ];

  const result = convertJsonToCsv(records, [
    "generic,name",
    'brand"name',
  ]);

  assert.equal(
    result,
    '"generic,name","brand""name"\r\nAlbuterol,Ventolin'
  );
});
