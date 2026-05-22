import { describe, it, expect } from "vitest";
import { validateReadOnly, findMissingPartitionFilters, extractTableRefs, formatResultWarning, type Catalog } from "./catalog.js";

describe("validateReadOnly", () => {
	it("accepts allowed verbs", () => {
		expect(validateReadOnly("SELECT 1")).toBeNull();
		expect(validateReadOnly("WITH x AS (SELECT 1) SELECT * FROM x")).toBeNull();
		expect(validateReadOnly("SHOW TABLES")).toBeNull();
		expect(validateReadOnly("DESCRIBE ukb_ppp.assays")).toBeNull();
		expect(validateReadOnly("EXPLAIN SELECT 1")).toBeNull();
	});

	it("accepts lowercase and leading whitespace", () => {
		expect(validateReadOnly("  select 1")).toBeNull();
		expect(validateReadOnly("\n\twith x as (select 1) select * from x")).toBeNull();
	});

	it("rejects write/DDL verbs", () => {
		expect(validateReadOnly("DROP TABLE x")).toMatch(/Only SELECT/);
		expect(validateReadOnly("INSERT INTO x VALUES (1)")).toMatch(/Only SELECT/);
		expect(validateReadOnly("UPDATE x SET a = 1")).toMatch(/Only SELECT/);
		expect(validateReadOnly("DELETE FROM x")).toMatch(/Only SELECT/);
		expect(validateReadOnly("CREATE TABLE x (a INT)")).toMatch(/Only SELECT/);
	});

	it("rejects SQL comments", () => {
		expect(validateReadOnly("SELECT 1 -- comment")).toBe("SQL comments are not allowed.");
		expect(validateReadOnly("SELECT 1 /* comment */")).toBe("SQL comments are not allowed.");
	});

	it("accepts comment markers inside string literals", () => {
		expect(validateReadOnly("SELECT * FROM t WHERE name = 'foo--bar' LIMIT 1")).toBeNull();
		expect(validateReadOnly("SELECT * FROM t WHERE x = '/* not a comment */' LIMIT 1")).toBeNull();
	});

	it("accepts SQL '' escape for embedded single quote", () => {
		expect(validateReadOnly("SELECT * FROM t WHERE name = 'O''Brien' LIMIT 1")).toBeNull();
	});

	it("rejects real comments even when string literals are present", () => {
		expect(validateReadOnly("SELECT * FROM t WHERE name = 'foo' -- trailing")).toBe("SQL comments are not allowed.");
		expect(validateReadOnly("/* leading */ SELECT 1")).toBe("SQL comments are not allowed.");
	});
});

describe("findMissingPartitionFilters", () => {
	it("returns empty for unpartitioned tables regardless of WHERE", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				dbsnp: {
					id: "dbsnp", name: "dbSNP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						variants: {
							description: "", partition_by: [], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		expect(findMissingPartitionFilters("SELECT rsid FROM dbsnp.variants LIMIT 10", catalog)).toEqual([]);
	});

	it("returns empty when all partition cols appear in WHERE", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry", "protein_id"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = "SELECT * FROM ukb_ppp.pqtls WHERE ancestry = 'EUR' AND protein_id = 'P43220' LIMIT 10";
		expect(findMissingPartitionFilters(sql, catalog)).toEqual([]);
	});

	it("reports missing partition cols", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry", "protein_id"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const result = findMissingPartitionFilters("SELECT * FROM ukb_ppp.pqtls WHERE ancestry = 'EUR' LIMIT 10", catalog);
		expect(result).toEqual([{ ns: "ukb_ppp", table: "pqtls", partitionCols: ["ancestry", "protein_id"], missing: ["protein_id"] }]);
	});

	it("reports all partition cols missing when WHERE is absent", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry", "protein_id"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const result = findMissingPartitionFilters("SELECT * FROM ukb_ppp.pqtls LIMIT 10", catalog);
		expect(result[0].missing).toEqual(["ancestry", "protein_id"]);
	});

	it("matches lowercase and multi-line SQL", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = "select *\nfrom ukb_ppp.pqtls\nwhere ancestry = 'EUR'\nlimit 10";
		expect(findMissingPartitionFilters(sql, catalog)).toEqual([]);
	});

	it("ignores unknown ns.table references", () => {
		const catalog: Catalog = { version: 1, namespaces: {} };
		expect(findMissingPartitionFilters("SELECT * FROM unknown.table LIMIT 1", catalog)).toEqual([]);
	});

	it("returns empty for non-SELECT/WITH queries even when table is partitioned", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		expect(findMissingPartitionFilters("DESCRIBE ukb_ppp.pqtls", catalog)).toEqual([]);
	});

	it("does not satisfy partition requirement from a string literal that matches the column name", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = "SELECT * FROM ukb_ppp.pqtls WHERE protein_id = 'ancestry' LIMIT 1";
		const result = findMissingPartitionFilters(sql, catalog);
		expect(result).toEqual([{ ns: "ukb_ppp", table: "pqtls", partitionCols: ["ancestry"], missing: ["ancestry"] }]);
	});

	it("does not match table references that appear inside string literals", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
				dbsnp: {
					id: "dbsnp", name: "dbSNP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						variants: {
							description: "", partition_by: [], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = "SELECT * FROM dbsnp.variants WHERE source = 'from ukb_ppp.pqtls' LIMIT 1";
		expect(findMissingPartitionFilters(sql, catalog)).toEqual([]);
	});

	it("matches partition columns referenced via double-quoted identifiers", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = `SELECT * FROM ukb_ppp.pqtls WHERE "ancestry" = 'EUR' LIMIT 1`;
		expect(findMissingPartitionFilters(sql, catalog)).toEqual([]);
	});

	it("reports missing partition cols on JOINed tables", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						assays: {
							description: "", partition_by: [], sort_by: [], related_tables: {}, columns: [],
						},
						pqtls: {
							description: "", partition_by: ["ancestry", "protein_id"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = "SELECT a.gene_symbol, p.pvalue FROM ukb_ppp.assays a JOIN ukb_ppp.pqtls p ON a.protein_id = p.protein_id LIMIT 10";
		const result = findMissingPartitionFilters(sql, catalog);
		expect(result).toEqual([{ ns: "ukb_ppp", table: "pqtls", partitionCols: ["ancestry", "protein_id"], missing: ["ancestry", "protein_id"] }]);
	});

	// Known limitation: aliasing like FROM ns.t AS p WHERE p.ancestry = 'EUR' still satisfies the
	// substring check because the column name appears in the WHERE clause. This is the desired
	// behavior; pinned to catch regressions if the matcher gets stricter.
	it("accepts table aliases that reference partition columns", () => {
		const catalog: Catalog = {
			version: 1,
			namespaces: {
				ukb_ppp: {
					id: "ukb_ppp", name: "UKB PPP", description: "", citation: {}, source_url: "", license: "",
					tables: {
						pqtls: {
							description: "", partition_by: ["ancestry"], sort_by: [], related_tables: {}, columns: [],
						},
					},
				},
			},
		};
		const sql = "SELECT p.* FROM ukb_ppp.pqtls AS p WHERE p.ancestry = 'EUR' LIMIT 1";
		expect(findMissingPartitionFilters(sql, catalog)).toEqual([]);
	});
});

describe("extractTableRefs", () => {
	it("returns empty for queries with no qualified table refs", () => {
		expect(extractTableRefs("SELECT 1")).toEqual([]);
		expect(extractTableRefs("SELECT * FROM unqualified LIMIT 1")).toEqual([]);
	});

	it("extracts a single FROM ref", () => {
		expect(extractTableRefs("SELECT * FROM ukb_ppp.pqtls LIMIT 1")).toEqual([{ ns: "ukb_ppp", table: "pqtls" }]);
	});

	it("extracts FROM and JOIN refs together", () => {
		const sql = "SELECT * FROM ukb_ppp.assays a JOIN ukb_ppp.pqtls p ON a.protein_id = p.protein_id LIMIT 1";
		expect(extractTableRefs(sql)).toEqual([
			{ ns: "ukb_ppp", table: "assays" },
			{ ns: "ukb_ppp", table: "pqtls" },
		]);
	});

	it("matches all JOIN variants (INNER, LEFT, RIGHT, FULL OUTER, CROSS)", () => {
		const sql = `SELECT * FROM a.t1
			INNER JOIN b.t2 ON 1=1
			LEFT JOIN c.t3 ON 1=1
			RIGHT OUTER JOIN d.t4 ON 1=1
			FULL OUTER JOIN e.t5 ON 1=1
			CROSS JOIN f.t6
			LIMIT 1`;
		expect(extractTableRefs(sql)).toEqual([
			{ ns: "a", table: "t1" },
			{ ns: "b", table: "t2" },
			{ ns: "c", table: "t3" },
			{ ns: "d", table: "t4" },
			{ ns: "e", table: "t5" },
			{ ns: "f", table: "t6" },
		]);
	});

	it("deduplicates self-joins", () => {
		const sql = "SELECT * FROM ukb_ppp.pqtls a JOIN ukb_ppp.pqtls b ON a.protein_id = b.protein_id LIMIT 1";
		expect(extractTableRefs(sql)).toEqual([{ ns: "ukb_ppp", table: "pqtls" }]);
	});

	it("ignores ns.table references inside string literals", () => {
		const sql = "SELECT * FROM dbsnp.variants WHERE source = 'from ukb_ppp.pqtls' LIMIT 1";
		expect(extractTableRefs(sql)).toEqual([{ ns: "dbsnp", table: "variants" }]);
	});

	it("lowercases ns and table", () => {
		expect(extractTableRefs("SELECT * FROM UKB_PPP.PQTLS LIMIT 1")).toEqual([{ ns: "ukb_ppp", table: "pqtls" }]);
	});

	it("extracts refs from CTEs and subqueries", () => {
		const sql = "WITH x AS (SELECT * FROM ns1.t1) SELECT * FROM x JOIN (SELECT * FROM ns2.t2) y ON 1=1 LIMIT 1";
		expect(extractTableRefs(sql)).toEqual([
			{ ns: "ns1", table: "t1" },
			{ ns: "ns2", table: "t2" },
		]);
	});
});

describe("formatResultWarning", () => {
	it("returns empty string for normal small result", () => {
		expect(formatResultWarning(5, 5, "SELECT * FROM t LIMIT 10", 100)).toBe("");
	});

	it("warns on truncation when allRows exceeds maxRows", () => {
		const w = formatResultWarning(100, 250, "SELECT * FROM t LIMIT 500", 100);
		expect(w).toContain("truncated from 250 to 100 rows");
	});

	it("warns when rows hit the LIMIT clause", () => {
		const w = formatResultWarning(10, 10, "SELECT * FROM t LIMIT 10", 100);
		expect(w).toContain("maximum number of rows");
	});

	it("does not warn on LIMIT 1", () => {
		expect(formatResultWarning(1, 1, "SELECT * FROM t LIMIT 1", 100)).toBe("");
	});

	it("prefers truncation warning over hit-limit warning when both apply", () => {
		const w = formatResultWarning(100, 250, "SELECT * FROM t LIMIT 100", 100);
		expect(w).toContain("truncated from 250");
		expect(w).not.toContain("maximum number of rows");
	});
});
