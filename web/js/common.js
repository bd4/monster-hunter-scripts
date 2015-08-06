// maps name -> [id]
WEAPON_NAME_IDX = {};

// maps id -> dict with keys:
//            ["name", "wtype", "final", "element", "element_2", "awaken"]
WEAPON_ID_IDX = {};

// maps weapon name name -> calculating palico id string
PALICO_ID = {};

_ITEM_NAME_SPECIAL = {
    "welldonesteak":	"Well-done Steak",
    "lrgelderdragonbone":	"Lrg ElderDragon Bone",
    "highqualitypelt":	"High-quality Pelt",
    "kingsfrill":   	"King's Frill",
    "btetsucabrahardclaw":	"B.TetsucabraHardclaw",
    "heartstoppingbeak":	"Heart-stopping Beak",
    "dsqueenconcentrate":	"D.S.QueenConcentrate",
    "dahrenstone":  	"Dah'renstone",
    "championsweapon":	"Champion's Weapon",
    "championsarmor":	"Champion's Armor",
    "popeyedgoldfish":	"Pop-eyed Goldfish",
    "100mwantedposter":	"100m+ Wanted Poster",
    "goddesssmelody":	"Goddess's Melody",
    "goddesssembrace":	"Goddess's Embrace",
    "capcommhspissue":	"Capcom MH Sp. Issue",
    "goddesssfire": 	"Goddess's Fire",
    "huntersticket":	"Hunter's Ticket",
    "herosseal":    	"Hero's Seal",
    "thetaleofpoogie":	"The Tale of Poogie",
    "goddesssgrace":	"Goddess's Grace",
    "conquerorsseal":	"Conqueror's Seal",
    "conquerorssealg":	"Conqueror's Seal G",
    "questersticket":	"Quester's Ticket",
    "instructorsticket":"Instructor's Ticket",
    "veticket":         "VE Ticket",
    "vedeluxeticket":	"VE Deluxe Ticket",
    "vebronzeticket":	"VE Bronze Ticket",
    "vesilverticket":	"VE Silver Ticket",
    "vegoldenticket":	"VE Golden Ticket",
    "vecosmicticket":	"VE Cosmic Ticket"
};

WEAPON_TYPE_ABBR = {
    "Great Sword":  	"GS",
    "Long Sword":    	"LS",
    "Sword and Shield":	"Sw",
    "Dual Blades":	    "DB",
    "Hammer":	        "Ha",
    "Hunting Horn":	    "HH",
    "Lance":	        "La",
    "Gunlance":	        "GL",
    "Switch Axe":	    "SA",
    "Charge Blade":	    "CB",
    "Insect Glaive":	"IG",
    "Light Bowgun":	    "LBG",
    "Heavy Bowgun":	    "HBG",
    "Bow":      	    "Bow"
};

ELEMENT_ABBR = {
    "Fire":         "Fi",
    "Water":        "Wa",
    "Thunder":      "Th",
    "Ice":          "Ic",
    "Dragon":       "Dr",
    "Poison":       "Po",
    "Paralysis":    "Pa",
    "Sleep":        "Sl",
    "Blashblight":  "Bl"
};

(function($) {
    $.QueryString = (function(a) {
        if (a == "") return {};
        var b = {};
        for (var i = 0; i < a.length; ++i)
        {
            var p=a[i].split('=');
            if (p.length != 2) continue;
            b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
        }
        return b;
    })(window.location.search.substr(1).split('&'))
})(jQuery);


function encode_utf8(s) {
    return unescape(encodeURIComponent(s));
}


function encode_qs(obj) {
    var params = [];
    for (var key in obj) {
        if (!obj.hasOwnProperty(key)) continue;
        params.push(encodeURIComponent(key) + "="
                    + encodeURIComponent(obj[key]));
    }
    return params.join("&");
}


function get_base_path() {
    var path = document.location.pathname;
    return path.substring(0, path.lastIndexOf('/'));
}


function _item_name_key(s) {
    return s.replace(RegExp("[ .'+-]","g"), '').toLowerCase();
}


function normalize_name(s) {
    var key = _item_name_key(s);
    if (_ITEM_NAME_SPECIAL[key]) {
        return _ITEM_NAME_SPECIAL[key];
    }
    var chars = s.split("");
    var cap_next = true;
    var i;
    for (i=0; i<chars.length; i++) {
        if (cap_next) {
            chars[i] = chars[i].toUpperCase();
            cap_next = false;
        } else if (chars[i] == "." || chars[i] == " " || chars[i] == "-") {
            cap_next = true;
        } else {
            chars[i] = chars[i].toLowerCase();
        }
    }
    return chars.join("");
}


function setup_item_autocomplete(selector) {
  var DATA_PATH = get_base_path() + "/rewards/";
  $.getJSON(DATA_PATH + "items.json",
            function(data) {
                $(selector).autocomplete({ source: data });
            });
}


function load_weapon_data(ready_fn) {
    var DATA_PATH = get_base_path() + "/jsonapi/";
    $.getJSON(DATA_PATH + "weapon/_index_name.json",
              function(data) {
                  WEAPON_NAME_IDX = data;
                  $.getJSON(DATA_PATH + "weapon/_index_id.json",
                            function(data) {
                                WEAPON_ID_IDX = data;
                                ready_fn();
                            });
              });
}


function load_calculating_palico_data(ready_fn) {
    var DATA_PATH = get_base_path() + "/data/";
    $.getJSON(DATA_PATH + "calculating_palico_weapon_map.json",
              function(data) {
                  PALICO_ID = data;
                  ready_fn();
              });
}



function setup_weapon_autocomplete(weapon_selector, predicate_fn, ready_fn,
                                   change_fn) {
    load_weapon_data(function() {
        update_weapon_autocomplete(
                             weapon_selector,
                             predicate_fn,
                             change_fn);
        if (ready_fn) {
            ready_fn();
        }
    });
}


function update_weapon_autocomplete(weapon_selector, predicate_fn, change_fn) {
    //alert("set weapon type " + type + " (" + weapon_selector + ")");
    source = [];
    $.each(WEAPON_ID_IDX, function(weapon_id, weapons) {
        var weapon_data = weapons[0];
        if (predicate_fn(weapon_data)) {
            var name = weapon_data["name"];
            if (name) {
                source.push(name);
            } else {
                console.log("WARN: weapon with no name '" + weapon_id + "'");
            }
        }
    });
    console.log("update weapon autocomplete len: " + source.length);
    console.log("weapon_selector = '" + weapon_selector + "'");
    $(weapon_selector).autocomplete(
      { source: source,
        change: function (event, ui) {
            if (!ui.item) return;
            console.log("weapon autocomplete change");
            if (change_fn) {
                change_fn();
            }
        }
      }
    );
    $(weapon_selector).keypress(function(e) {
       if (e.which == 13 && change_fn) {
           console.log("weapon enter keypress");
           change_fn();
       }
    });
}


function set_sharpness_titles(weapon_data) {
    if (weapon_data["sharpness"]) {
        weapon_data["sharpness_title"] =
              weapon_data["sharpness"].join(",");
        weapon_data["sharpness_plus_title"] =
              weapon_data["sharpness_plus"].join(",");
        weapon_data["sharpness_all_title"] =
          weapon_data["sharpness_title"] + " ("
          + weapon_data["sharpness_plus_title"] + ")";
    } else {
        // gunner weapons have no sharpness
        weapon_data["sharpness_title"] = "";
        weapon_data["sharpness_plus_title"] = "";
        weapon_data["sharpness_all_title"] = "";
    }
}


function set_horn_melodies_title(weapon_data) {
    if (! weapon_data["horn_notes"]) {
        weapon_data["horn_melodies_title"] = ""
        return;
    }

    var lines = [];
    $.each(weapon_data["horn_melodies"], function(i, melody) {
        var space = Array(6 - melody["song"].length).join("&nbsp;");
        lines.push(melody["song"] + space + melody["effect1"]);
    });
    weapon_data["horn_melodies_title"] = lines.join("&#10;");
}


function get_calculating_palico_setup(weapon_data) {
    // NB: load_calculating_palico_data must be called first
    var name = weapon_data["name"];
    if (! name in PALICO_ID) {
        return "";
    }

    var setup = [];
    setup.push(PALICO_ID[name]);
    var sharpness_plus = weapon_data["sharpness_plus"];
    var max_sharpness = -1;
    for (var i=0; i < sharpness_plus.length; i++) {
        if (sharpness_plus[i] == 0) {
            break;
        }
        max_sharpness = i;
    }
    setup.push(max_sharpness);
    setup.push("3.1.awk,shp");
    return setup.join(".");
}

function get_calculating_palico_uri(setups) {
    // m=31 is Great Jaggi
    var base = "http://minyoung.ch/calculatingpalico/?m=31&s=";
    return base + encodeURIComponent(JSON.stringify(setups));
}
