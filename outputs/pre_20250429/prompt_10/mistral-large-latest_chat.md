Given the query and the context information provided, we need to match the item "Maize starch, citric acid" sourced from China to the best matching description from the list.

The lookup string pattern is:
`<product name> {<2-letter ISO Code for region>} | <activity name> | Cut-off, U`

For the item "Maize starch, citric acid" sourced from China, the lookup string should be:
- Product name: "Maize starch"
- Region: "CN" (China)
- Activity name: "citric acid production"
- Suffix: "Cut-off, U"

Thus, the lookup string should be:
`"Maize starch {CN}| citric acid production | Cut-off, U"`

From the context information provided:
```
'Maize starch {RNA}| citric acid production | Cut-off, U',
'Cast iron removed by drilling, computer numerical controlled {GLO}| market for | Cut-off, U',
'Maize starch {RoW}| citric acid production | Cut-off, U',
'Chromium steel removed by turning, primarily roughing, conventional {RoW}| chromium steel turning, primarily roughing, conventional | Cut-off, U',
'Maize starch {CN}| citric acid production | Cut-off, U'
```

The best matching description is:
`"Maize starch {CN}| citric acid production | Cut-off, U"`

Therefore, the answer is:
```json
{
  "best_lookup_string": "Maize starch {CN}| citric acid production | Cut-off, U"
}
```