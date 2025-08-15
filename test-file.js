const fs = require('fs');

console.log('Testing file read with UTF-16 and BOM removal...');
try {
    // Read as UTF-16 LE (Little Endian)
    let data = fs.readFileSync('./demo-results/search-proof/all-docs.json', 'utf16le');

    // Strip BOM if present (first character)
    if (data.charCodeAt(0) === 0xFEFF) {
        data = data.slice(1);
        console.log('✅ BOM removed');
    }

    console.log('File size after BOM removal:', data.length);
    console.log('First 100 characters:');
    console.log(data.substring(0, 100));

    // Try parsing
    const parsed = JSON.parse(data);
    console.log('✅ JSON is valid!');
    console.log('Document count:', parsed.hits.hits.length);
} catch (error) {
    console.error('❌ Error:', error.message);
    console.log('First char code:', data.charCodeAt(0));
}