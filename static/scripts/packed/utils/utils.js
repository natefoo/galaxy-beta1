define(["libs/underscore"],function(c){function f(j,i,h){var k=new XMLHttpRequest();k.open("GET",j,true);k.setRequestHeader("Accept","application/json");k.setRequestHeader("Cache-Control","no-cache");k.setRequestHeader("X-Requested-With","XMLHttpRequest");k.onloadend=function(){var l=k.status;if(l==200){try{response=jQuery.parseJSON(k.responseText)}catch(m){response=k.responseText}i&&i(response)}else{h&&h(l)}};k.send()}function b(k,h){var i=$('<div class="'+k+'"></div>');i.appendTo(":eq(0)");var j=i.css(h);i.remove();return j}function a(h){if(!$('link[href^="'+h+'"]').length){$('<link href="'+galaxy_config.root+h+'" rel="stylesheet">').appendTo("head")}}function g(h,i){if(h){return c.defaults(h,i)}else{return i}}function d(i,k){var j="";if(i>=100000000000){i=i/100000000000;j="TB"}else{if(i>=100000000){i=i/100000000;j="GB"}else{if(i>=100000){i=i/100000;j="MB"}else{if(i>=100){i=i/100;j="KB"}else{if(i>0){i=i*10;j="b"}else{return"<strong>-</strong>"}}}}}var h=(Math.round(i)/10);if(k){return h+" "+j}else{return"<strong>"+h+"</strong> "+j}}function e(){return(new Date().getTime()).toString(36)}return{cssLoadFile:a,cssGetAttribute:b,jsonFromUrl:f,merge:g,bytesToString:d,uuid:e}});