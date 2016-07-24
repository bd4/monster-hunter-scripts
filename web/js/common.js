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
    if (typeof DATA_PATH == "undefined") {
        DATA_PATH = get_base_path() + "/jsonapi/";
    }
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
        if (weapon_data["sharpness_plus2"]) {
            weapon_data["sharpness_plus2_title"] =
                  weapon_data["sharpness_plus2"].join(",");
            weapon_data["sharpness_all_title"] =
              weapon_data["sharpness_title"] + "; "
              + weapon_data["sharpness_plus_title"] + "; "
              + weapon_data["sharpness_plus2_title"];
        }
    } else {
        // gunner weapons have no sharpness
        weapon_data["sharpness_title"] = "";
        weapon_data["sharpness_plus_title"] = "";
        weapon_data["sharpness_all_title"] = "";
    }
}


function set_bow_values(weapon_data) {
    if (weapon_data["wtype"] != "Bow") {
        return;
    }

    // translate mh4u data to be consistant with mhx data
    if (weapon_data["charges"]) {
        var charges = weapon_data["charges"].split("|");
        var parts;
        var shot;
        var shot_types = [];
        $.each(charges, function(i, charge) {
            shot = {};
            parts = charge.split(" ");
            shot["type"] = parts[0];
            shot["level"] = parts[1][1];
            shot["requires_loading"] = parts[1].endsWith("*");
            shot_types.push(shot);
        });
        weapon_data["shot_types"] = shot_types;

        var coatings = weapon_data["coatings"].split("|");
        var parts;
        var coating;
        var ammo_list = [];
        $.each(coatings, function(i, coating) {
            if (coating != "-") {
                ammo_list.push(coating);
            }
        });
        weapon_data["ammo"] = ammo_list;

        weapon_data["arc_type"] = weapon_data["recoil"];
    }

    var shots_text = [];
    var shot_text;
    $.each(weapon_data["shot_types"], function(i, shot) {
        shot_text = shot["type"].substring(0, 1) + shot["level"];
        if (shot["requires_loading"]) {
            shot_text = "(" + shot_text + ")";
        }
        shots_text.push(shot_text);
    });
    weapon_data["bow_shots_text"] = shots_text.join(" ");

    var coatings_text = [];
    var coating_text;
    $.each(weapon_data["ammo"], function(i, coating) {
        if (coating.startsWith("Power ")) {
            coating_text = "P" + coating.substring(6, 7);
        } else if (coating.startsWith("Element ")) {
            coating_text = "E" + coating.substring(8, 9);
        } else {
            coating_text = coating.substring(0, 3);
        }
        coatings_text.push(coating_text);
    });

    weapon_data["bow_coatings_text"] = coatings_text.join(" ");
}


function set_horn_melodies_title(weapon_data, melody_map) {
    if (! weapon_data["horn_notes"]) {
        weapon_data["horn_melodies_title"] = "";
        return;
    }

    var notes = weapon_data["horn_notes"];

    var melodies;
    if (melody_map) {
        melodies = melody_map[notes];
        if (! melodies) {
            // Try flipping second two notes if not found, mhx data is
            // either wrong or game itself is inconsistant about note
            // order.
            notes = notes.substring(0, 1) + notes.substring(2, 3)
                    + notes.substring(1, 2);
            melodies = melody_map[notes];
            if (melodies) {
                weapon_data["horn_notes"] = notes;
            }
        }
    } else {
        melodies = weapon_data["horn_melodies"];
    }

    if (! melodies) {
        var msg = "Unknown melodies for " + notes;
        weapon_data["horn_melodies_title"] = msg;
        console.log(msg);
        return;
    }

    var lines = [];
    $.each(melodies, function(i, melody) {
        var space = Array(6 - melody["song"].length).join("&nbsp;");
        lines.push(melody["song"] + space + melody["effect1"]);
    });
    weapon_data["horn_melodies_title"] = lines.join("&#10;");
}


function get_object_as_text(obj) {
    /*
    var max_len = 0;
    $.each(obj, function(k, v) {
        if (k.length > max_len)
            max_len = k.length
    });
    */
    var keys = Object.keys(obj);
    keys.sort();
    var lines = [];
    $.each(keys, function(i, key) {
        //var space = Array(2 + max_len - key.length).join(" ");
        lines.push(key + " " + obj[key]);
    });
    return lines.join(", ");
}


function object_add_values(dst_obj, src_obj) {
    // update dst_obj with values from src_obj, adding them together if
    // the key is already in dst_obj
    $.each(src_obj, function(k, v) {
        if (k in dst_obj) {
            dst_obj[k] += v;
        } else {
            dst_obj[k] = v;
        }
    });
}


function get_calculating_palico_setup(weapon_data) {
    // NB: load_calculating_palico_data must be called first
    var name = weapon_data["name"];
    if (! (name in PALICO_ID)) {
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
    setup.push("0.1.awk,shp");
    return setup.join(".");
}

function get_calculating_palico_uri(setups) {
    // m=31 is Great Jaggi
    var base = "http://minyoung.ch/calculatingpalico/?m=31&s=";
    return base + encodeURIComponent(JSON.stringify(setups));
}


function get_weapon_sort_values(weapon_data) {
    // Note: javascript does string coersion when comparing lists,
    // so this can't be used directly, see cmp_arrays.
    var sharp_reverse;
    if (weapon_data["sharpness"]) {
        sharp_reverse = Array.prototype.slice.call(weapon_data["sharpness"]);
        sharp_reverse.reverse();
    } else {
        sharp_reverse = null;
    }

    return [
        weapon_data["attack"],
        sharp_reverse,
        weapon_data["element_attack"],
        weapon_data["affinity"],
        weapon_data["num_slots"],
        weapon_data["defense"]
    ];
}


function cmp_arrays(alist, blist) {
    var cmp;
    for (var i=0; i<alist.length; i++) {
        a = alist[i];
        b = blist[i];
        if (a == null || b == null) {
            // ignore
        } else if (typeof a == "object") {
            cmp = cmp_arrays(a, b);
            if (cmp != 0) {
                return cmp;
            }
        } else {
            if (a < b) {
                return -1;
            } else if (a > b) {
                return 1;
            }
        }
    }
    return 0;
}
