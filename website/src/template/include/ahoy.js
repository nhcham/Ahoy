var languagePacks = {};
var languages = [];
var languagesDef = {};

function loadLanguagePack(data)
{
    var zip_buffer = new Uint8Array(data);
    var zip = new JSZip(zip_buffer);
    $.each(zip.files, function (index, zipEntry) {
        if (zipEntry.options.dir)
            return;
        
        var basename = zipEntry.name.replace( /.*\//, "" )
        if (basename == 'languages.json')
        {
            languagesDef = JSON.parse(zipEntry.asText());
            return;
        }
    
        var buffer = zipEntry.asUint8Array();
        
        var pack = {};
        
        var offset = 0;
        
        function requireString(s)
        {
            var bs = ''
            for (var i = 0; i < s.length; i++)
                bs += String.fromCharCode(buffer[offset + i]);
            var result = (s == bs);
            offset += s.length
            // TODO: Actually require this string, thank you.
        }
        
        function readZString()
        {
            var result = "";
            while (true) {
                var c = String.fromCharCode(buffer[offset++]);
                if (c == '\0')
                    break;
                result += c;
            }
            return result;
        }
        
        function readInt()
        {
            var result = 0;
            var shift = 0;
            for (var i = 0; i < 4; i++)
            {
                var c = buffer[offset++] & 0xff;
                c <<= shift;
                result |= c;
                shift += 8;
            }
            return result;
        }
        
        function readByte()
        {
            return buffer[offset++] & 0xff;
        }
        
        requireString("AHOY_LANGUAGE_PACK\0");
        
        pack.languageTag = readZString();
        languages.push(pack.languageTag);
        var version = readZString();
        
        pack.extraSlots = readInt();
        pack.prefixStart = readInt();
        pack.prefixEnd = readInt();
        pack.escapeOffset = readInt();
        pack.alphabetLength = readInt();
        pack.huffmanKeyDefault = readInt();
        pack.huffmanKeyEscape = readInt();
        pack.huffmanKeyWordOffsets = readInt();
        pack.huffmanKeyMonograms = readInt();
        pack.huffmanKeyBigrams = readInt();
        pack.huffmanKeyCount = readInt();
        
        pack.alphabet = [];
        pack.alphabetLookup = {};
        
        // read alphabet
        for (var i = 0; i < pack.alphabetLength; i++)
        {
            var codePoint = readInt();
            pack.alphabet.push(codePoint);
            pack.alphabetLookup[codePoint] = i;
        }
        
        // now parse lowercase entries
        pack.lowercase = [];
        
        for (var i = 0; i < pack.escapeOffset - pack.prefixEnd; i++)
            pack.lowercase.push(readInt());
        
        // now parse the Huffman keys
        pack.huffmanTrees = {};
        pack.huffmanKeys = [];
        
        for (var i = 0; i < pack.huffmanKeyCount; i++)
        {
            var huffmanKey = readInt();
            pack.huffmanKeys.push(huffmanKey);
            var codePointCount = pack.escapeOffset + 1;
            if (huffmanKey == pack.huffmanKeyEscape)
                codePointCount = pack.alphabetLength - pack.escapeOffset - 1;
            pack.huffmanTrees[huffmanKey] = [];
        }
        
        for (var i = 0; i < pack.huffmanKeyCount; i++)
        {
            var huffmanKey = pack.huffmanKeys[i];
            
            var codePointCount = pack.escapeOffset + 1;
            if (huffmanKey == pack.huffmanKeyEscape)
                codePointCount = pack.alphabetLength - pack.escapeOffset - 1;
            
            for (var k = 0; k < codePointCount; k++)
                pack.huffmanTrees[huffmanKey].push(readByte());
        }
                
        var row = $('<tr>');

        var cell = $('<td>');
        cell.text(pack.languageTag);
        row.append(cell);

        cell = $('<td>');
        cell.text(languagesDef[pack.languageTag]['native']);
        row.append(cell);

        cell = $('<td>');
        if (languagesDef[pack.languageTag]['status'] === undefined)
            cell.html("unknown &ndash; <a href='lang/details-" + pack.languageTag + ".html'>input required</a>");
        else if (languagesDef[pack.languageTag]['status'] === 'published')
        {
            cell.html("published");
            cell.css('background-color', '#73d216');
        }
        else if (languagesDef[pack.languageTag]['status'] === 'draft')
        {
            cell.html("draft &ndash; <a href='lang/details-" + pack.languageTag + ".html'>confirmation required</a>");
            cell.css('background-color', '#b8de32');
        }
        else if (languagesDef[pack.languageTag]['status'] === 'sketch')
        {
            cell.html("rough draft &ndash; <a href='lang/details-" + pack.languageTag + ".html'>input required</a>");
            cell.css('background-color', '#fce94f');
        }
        row.append(cell);

        cell = $("<td style='text-align: right;' id='ml-" + pack.languageTag + "'>");
        cell.html('&ndash;');
        row.append(cell);

        cell = $('<td>');
        var note = $("<span style='display: none;' id='cannot-" + pack.languageTag + "'>Cannot use this language pack to encode your message.</span>");
        cell.append(note);
        var bar = $("<div class='progress'><div id='bar-" + pack.languageTag + "'></div></div>");
        cell.append(bar);
        row.append(cell);

        row.data('lang', pack.languageTag);
        row.attr('id', 'row-lang-' + pack.languageTag);
        $('#barchart').append(row);
        
        languagePacks[pack.languageTag] = pack;
        
    });    
    
    console.log("Finished!");
    $('#message').keyup(function() {
        var message = $('#message').val();
        encode(message);
    });
    encode($('#message').val());
    var widths = [];
    $('#barchart tr').each(function(index, row) {
        if (index == 0)
        {
            $(row).children('th').each(function(index2, cell) {
                widths.push($(cell).width());
                $(cell).width(widths[index2] + 5);
            });
        }
    });
    $('#best tr').each(function(index, row) {
        if (index == 0)
        {
            $(row).children('th').each(function(index2, cell) {
                $(cell).width(widths[index2] + 5);
            });
        }
    });
    $('#message').focus();
}

$(document).ready(function() {
    $.get('include/ahoy-language-packs.zip', function(data) {
        loadLanguagePack(data);
    }, 'binary');
});


function encode(message)
{
    var lengthForLanguage = {};
    var bestLanguageLength = null;
    var bestLanguageTag = null;
    jQuery.each(languages, function(index, lang) {
        var length = getEncodedMessageLength(languagePacks[lang], message);
        if (length > 0 && (
            (bestLanguageLength == null) || 
            (length < bestLanguageLength) ||
            ((length == bestLanguageLength) && (lang < bestLanguageTag))))
        {
            bestLanguageLength = length;
            bestLanguageTag = lang;
        }
        
        lengthForLanguage[lang] = length;
        if (length < 0)
        {
            $('#ml-' + lang).html('&ndash;');
            $('#bar-' + lang).toggleClass('over', false);
            $('#bar-' + lang).css('width', '0%');
            $('#bar-' + lang).parent().hide();
            $('#cannot-' + lang).show();
        }
        else
        {
            $('#ml-' + lang).html('' + length + ' bits');
            $('#bar-' + lang).toggleClass('over', length > 172);
            $('#bar-' + lang).css('width', '' + ((length > 172 ? 172 : length) * 100.0 / 172) + '%');
            $('#bar-' + lang).parent().show();
            $('#cannot-' + lang).hide();
        }
    });
    
    $('#best tr').each(function(index, element) {
        if ($(element).attr('id') === 'best_header' || $(element).attr('id') === 'best_placeholder')
            return;
        $('#barchart').append($(element).detach());
    });
    
    if (bestLanguageTag != null)
    {
        var element = $('#row-lang-' + bestLanguageTag).detach();
        $('#best').append(element);
        $('#best_placeholder').hide();
    }
    else
    {
        if (message.length == 0)
            $('#best_placeholder td').html("Please enter a message.");
        else
            $('#best_placeholder td').html("<img src='include/dialog-warning.png' style='float: left; margin-top: 1em; margin-right: 1em;' /><p>There is currently no language pack which is able to encode your message. Please help to improve the App by getting in contact with <a href='mailto:info@nhcham.org'>info@nhcham.org</a> and request the addition of a language or the addition of missing characters.</p>");
        $('#best_placeholder').show();
    }
    
    $('#barchart tr').sortElements(function(a, b) {
        var bitLengthA = lengthForLanguage[$(a).data('lang')];
        var bitLengthB = lengthForLanguage[$(b).data('lang')];
        if (bitLengthA < 0)
            bitLengthA = 999999;
        if (bitLengthB < 0)
            bitLengthB = 999999;
        if (bitLengthA == bitLengthB)
            return $(a).data('lang') > $(b).data('lang') ? 1 : -1;
        else
            return bitLengthA > bitLengthB ? 1 : -1;
    });
}

function getEncodedMessageLength(pack, s)
{
    var bitLength = 0;
    var ci2 = -1;
    var ci1 = -1;
    var wordOffset = 0;
    for (var i = 0; i < s.length; i++)
    {
        var codePoint = s.charCodeAt(i);
        if (codePoint in pack.alphabetLookup)
        {
            var huffmanKey = pack.huffmanKeyDefault;
            if (wordOffset >= 0 && wordOffset < pack.extraSlots)
            {
                var testKey = pack.huffmanKeyWordOffset + wordOffset;
                if (testKey in pack.huffmanTrees)
                    huffmanKey = testKey;
            }
            if (ci1 >= pack.prefixStart && ci1 < pack.prefixEnd)
            {
                var testKey = pack.huffmanKeyMonograms + (ci1 - pack.prefixStart);
                if (testKey in pack.huffmanTrees)
                    huffmanKey = testKey;
            }
            if (ci1 >= pack.prefixStart && ci1 < pack.prefixEnd && ci2 >= pack.prefixStart && ci2 < pack.prefixEnd)
            {
                var testKey = pack.huffmanKeyBigrams + (ci2 - pack.prefixStart) * (pack.prefixEnd - pack.prefixStart) + (ci1 - pack.prefixStart);
                if (testKey in pack.huffmanTrees)
                    huffmanKey = testKey;
            }
            
            var ci = pack.alphabetLookup[codePoint];
            var delta = 0;
            if (ci < pack.escapeOffset)
                delta = pack.huffmanTrees[huffmanKey][ci];
            else
                delta = pack.huffmanTrees[huffmanKey][pack.escapeOffset] + pack.huffmanTrees[pack.huffmanKeyEscape][ci - pack.escapeOffset - 1];
            bitLength += delta;
            if (ci == 0)
            {
                ci2 = -1;
                ci1 = -1;
                wordOffset = 0;
            } else {
                ci2 = ci1;
                ci1 = ci;
                if (ci1 >= pack.prefixEnd && ci < pack.escapeOffset)
                    ci1 = pack.lowercase[ci1 - pack.prefixEnd];
                wordOffset++;
            }
        }
        else 
            return -1;
    }
    return bitLength;
}

// yanked from http://james.padolsey.com/javascript/sorting-elements-with-jquery/
jQuery.fn.sortElements = (function(){
 
    var sort = [].sort;
 
    return function(comparator, getSortable) {
 
        getSortable = getSortable || function(){return this;};
 
        var placements = this.map(function(){
 
            var sortElement = getSortable.call(this),
                parentNode = sortElement.parentNode,
 
                // Since the element itself will change position, we have
                // to have some way of storing its original position in
                // the DOM. The easiest way is to have a 'flag' node:
                nextSibling = parentNode.insertBefore(
                    document.createTextNode(''),
                    sortElement.nextSibling
                );
 
            return function() {
 
                if (parentNode === this) {
                    throw new Error(
                        "You can't sort elements if any one is a descendant of another."
                    );
                }
 
                // Insert before flag:
                parentNode.insertBefore(this, nextSibling);
                // Remove flag:
                parentNode.removeChild(nextSibling);
 
            };
 
        });
 
        return sort.call(this, comparator).each(function(i){
            placements[i].call(getSortable.call(this));
        });
 
    };
 
})();