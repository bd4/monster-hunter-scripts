WEAPON_NAME_IDX = {};
WEAPON_TYPE_IDX = {};

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


function setup_weapon_autocomplete(type_selector, weapon_selector, ready_fn,
                                   change_fn) {
    var DATA_PATH = get_base_path() + "/jsonapi/";
    $.getJSON(DATA_PATH + "weapon/_index_name.json",
              function(data) {
                  WEAPON_NAME_IDX = data;
                  $.getJSON(DATA_PATH + "weapon/_index_wtype.json",
                            function(data) {
                                WEAPON_TYPE_IDX = data;
                                if (ready_fn) {
                                    ready_fn();
                                }
                                _setup_weapon_autocomplete(
                                                     $(type_selector).val(),
                                                     weapon_selector,
                                                     change_fn);
                                $(type_selector).change(function(evt) {
                                    _setup_weapon_autocomplete(
                                                $(type_selector).val(),
                                                weapon_selector, change_fn);
                                });
                            });
              });
}

function _setup_weapon_autocomplete(type, weapon_selector, change_fn) {
    //alert("set weapon type " + type + " (" + weapon_selector + ")");
    var source;
    if (type == "All") {
        source = Object.keys(WEAPON_NAME_IDX);
        //alert(source[10]);
    } else {
        var object_list = WEAPON_TYPE_IDX[type];
        source = [];
        for (i=0; i<object_list.length; i++) {
            source.push(object_list[i]["name"]);
        }
    }
    $(weapon_selector).autocomplete(
      { source: source,
        change: function (event, ui) {
            if (!ui.item) return;
            if (change_fn) {
                change_fn(ui.item["value"]);
            }
        }
      }
    );
    $(weapon_selector).keypress(function(e) {
       if (e.which == 13 && change_fn) {
           change_fn($(weapon_selector).val());
       }
    });
}
