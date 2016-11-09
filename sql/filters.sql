-- TESTING
-- Endpoints work. Links almost work properly. (getting 3x correct value in test case)
SELECT decodeIP(`n`.ipstart) AS 'address'
  , `n`.alias AS 'hostname'
  , `n`.subnet AS 'subnet'
  , `sn`.kids AS 'endpoints'
  , COALESCE(`l_in`.links,0) / (COALESCE(`l_in`.links,0) + COALESCE(`l_out`.links,0)) AS 'ratio'
FROM Nodes AS `n`
LEFT JOIN (
    SELECT dst_start DIV 65536 * 65536 AS 'low'
        , dst_end DIV 65536 * 65536 + 65535 AS 'high'
        , sum(links) AS 'links'
    FROM LinksIn
    GROUP BY low, high
    ) AS `l_in`
ON `l_in`.low = `n`.ipstart AND `l_in`.high = `n`.ipend
LEFT JOIN (
    SELECT src_start DIV 65536 * 65536 AS 'low'
        , src_end DIV 65536 * 65536 + 65535 AS 'high'
        , sum(links) AS 'links'
    FROM LinksOut
    GROUP BY low, high
    ) AS `l_out`
ON `l_out`.low = `n`.ipstart AND `l_out`.high = `n`.ipend
LEFT JOIN (
    SELECT ipstart DIV 65536 * 65536 AS 'low'
        , ipend DIV 65536 * 65536 + 65535 AS 'high'
        , COUNT(ipstart) AS 'kids'
    FROM Nodes
    WHERE ipstart = ipend
    GROUP BY low, high
    ) AS `sn`
    ON `sn`.low = `n`.ipstart AND `sn`.high = `n`.ipend
WHERE `n`.ipstart BETWEEN 1325400064 AND 1342177279
    AND `n`.subnet BETWEEN 9 AND 16;


-- client and server connections, ratio test
-- 79. x.x.x range: 1325400064 .. 1342177279
-- 79.35.x.x range: 1327693824 .. 1327759359
SELECT SUM(links) FROM LinksIn WHERE dst_start = 1327693824 AND dst_end = 1327759359;
-- 29008
SELECT SUM(links) FROM LinksOut WHERE src_start = 1327693824 AND src_end = 1327759359;
-- 25
-- ratio: 0.9991389108944994
SELECT SUM(links) FROM Links WHERE dst BETWEEN 1327693824 AND 1327759359;
-- 29008
SELECT SUM(links) FROM Links WHERE src BETWEEN 1327693824 AND 1327759359;
-- 25


-- The problem is that it duplicates entries with the successive joins.
SELECT decodeIP(`n`.ipstart) AS 'address'
  , `n`.alias AS 'hostname'
  , `n`.subnet AS 'subnet'
  , COALESCE(sum(LinksIn.links),0) AS 'l_in'
  , COALESCE(sum(LinksOut.links),0) AS 'l_out'
FROM Nodes AS `n`
LEFT JOIN LinksIn
    ON LinksIn.dst_start = `n`.ipstart AND LinksIn.dst_end = `n`.ipend
LEFT JOIN LinksOut
    ON LinksOut.src_start = `n`.ipstart AND LinksOut.src_end = `n`.ipend
WHERE `n`.ipstart BETWEEN 1327693824 AND 1327759359
    AND `n`.subnet BETWEEN 9 AND 16
GROUP BY `n`.ipstart, `n`.subnet, `n`.alias;

  , COALESCE(sum(LinksIn.links),0) / (COALESCE(sum(LinksIn.links),0) + COALESCE(sum(LinksOut.links),0)) AS 'ratio'


-- 189.x.x.x
-- 3170893824 to 3187671039


-- Node Info COMBINED
SELECT CONCAT(decodeIP(n.ipstart), CONCAT('/', n.subnet)) AS 'address'
    , COALESCE(n.hostname, '') AS 'hostname'
    , l_out.unique_out_ip
    , l_out.unique_out_conn
    , COALESCE(l_out.total_out, 0) AS 'total_out'
    , l_in.unique_in_ip
    , l_in.unique_in_conn
    , COALESCE(l_in.total_in, 0) AS 'total_in'
    , COALESCE(l_in.ports_used, 0) AS 'ports_used'
    , t.seconds
FROM (
    SELECT ipstart, subnet, alias AS 'hostname'
    FROM Nodes
    WHERE ipstart = 352321536 AND ipend = 369098751
) AS n
LEFT JOIN (
    SELECT 352321536 AS 's1', COUNT(DISTINCT dst) AS 'unique_out_ip', COUNT(DISTINCT dst, port) AS 'unique_out_conn', SUM(links) AS 'total_out'
    FROM Links
    WHERE src BETWEEN 352321536 AND 369098751
    GROUP BY 's1'
) AS l_out
    ON n.ipstart = l_out.s1
LEFT JOIN (
    SELECT 352321536 AS 's1', COUNT(DISTINCT src) AS 'unique_in_ip', COUNT(DISTINCT src, port) AS 'unique_in_conn', SUM(links) AS 'total_in', COUNT(DISTINCT port) AS 'ports_used'
    FROM Links
    WHERE dst BETWEEN 352321536 AND 369098751
    GROUP BY 's1'
) AS l_in
    ON n.ipstart = l_in.s1
LEFT JOIN (
    SELECT 352321536 AS 's1'
        , (MAX(TIME_TO_SEC(timestamp)) - MIN(TIME_TO_SEC(timestamp))) AS 'seconds'
    FROM Links
    GROUP BY 's1'
) AS t
    ON n.ipstart = t.s1
LIMIT 1;


-- testing ratio for tables
SELECT CONCAT(decodeIP(ipstart), CONCAT('/', subnet)) AS 'address'
    , COALESCE(alias, '') AS 'alias'
    , COALESCE((SELECT SUM(links)
        FROM LinksOut AS l_out
        WHERE l_out.src_start = nodes.ipstart
          AND l_out.src_end = nodes.ipend
     ),0) AS "conn_out"
    , COALESCE((SELECT SUM(links)
        FROM LinksIn AS l_in
        WHERE l_in.dst_start = nodes.ipstart
          AND l_in.dst_end = nodes.ipend
     ),0) AS "conn_in"
FROM Nodes AS nodes
WHERE EXISTS (SELECT port FROM LinksOut WHERE LinksOut.port = '5061' && LinksOut.src_start = nodes.ipstart && LinksOut.src_end = nodes.ipend)
ORDER BY ipstart asc
LIMIT 0,10;


LEFT JOIN (
    SELECT dst_start DIV 65536 * 65536 AS 'low'
        , dst_end DIV 65536 * 65536 + 65535 AS 'high'
        , sum(links) AS 'links'
    FROM LinksIn
    GROUP BY low, high
    ) AS l_in
ON l_in.low = nodes.ipstart AND l_in.high = nodes.ipend