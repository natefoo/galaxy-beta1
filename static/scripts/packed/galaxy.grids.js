jQuery.ajaxSettings.traditional=true;define(["mvc/ui"],function(){var a=Backbone.Model.extend({defaults:{url_base:"",async:false,async_ops:[],categorical_filters:[],filters:{},sort_key:null,show_item_checkboxes:false,advanced_search:false,cur_page:1,num_pages:1,operation:undefined,item_ids:undefined},can_async_op:function(c){return _.indexOf(this.attributes.async_ops,c)!==-1},add_filter:function(g,h,d){if(d){var e=this.attributes.filters[g],c;if(e===null||e===undefined){c=h}else{if(typeof(e)=="string"){if(e=="All"){c=h}else{var f=[];f[0]=e;f[1]=h;c=f}}else{c=e;c.push(h)}}this.attributes.filters[g]=c}else{this.attributes.filters[g]=h}},remove_filter:function(d,g){var c=this.attributes.filters[d];if(c===null||c===undefined){return false}var f=true;if(typeof(c)==="string"){if(c=="All"){f=false}else{delete this.attributes.filters[d]}}else{var e=_.indexOf(c,g);if(e!==-1){c.splice(e,1)}else{f=false}}return f},get_url_data:function(){var c={async:this.attributes.async,sort:this.attributes.sort_key,page:this.attributes.cur_page,show_item_checkboxes:this.attributes.show_item_checkboxes,advanced_search:this.attributes.advanced_search};if(this.attributes.operation){c.operation=this.attributes.operation}if(this.attributes.item_ids){c.id=this.attributes.item_ids}var d=this;_.each(_.pairs(d.attributes.filters),function(e){c["f-"+e[0]]=e[1]});return c}});var b=Backbone.View.extend({grid:null,initialize:function(c){this.init_grid(c);this.init_grid_controls();$("input[type=text]").each(function(){$(this).click(function(){$(this).select()}).keyup(function(){$(this).css("font-style","normal")})})},init_grid:function(c){this.grid=c;this.init_grid_elements()},init_grid_controls:function(){$(".submit-image").each(function(){$(this).mousedown(function(){$(this).addClass("gray-background")});$(this).mouseup(function(){$(this).removeClass("gray-background")})});var c=this;$(".sort-link").each(function(){$(this).click(function(){c.set_sort_condition($(this).attr("sort_key"));return false})});$(".categorical-filter > a").each(function(){$(this).click(function(){c.set_categorical_filter($(this).attr("filter_key"),$(this).attr("filter_val"));return false})});$(".text-filter-form").each(function(){$(this).submit(function(){var g=$(this).attr("column_key");var f=$("#input-"+g+"-filter");var h=f.val();f.val("");c.add_filter_condition(g,h,true);return false})});var d=$("#input-tags-filter");if(d.length){d.autocomplete(this.grid.history_tag_autocomplete_url,{selectFirst:false,autoFill:false,highlight:false,mustMatch:false})}var e=$("#input-name-filter");if(e.length){e.autocomplete(this.grid.history_name_autocomplete_url,{selectFirst:false,autoFill:false,highlight:false,mustMatch:false})}$(".advanced-search-toggle").each(function(){$(this).click(function(){$("#standard-search").slideToggle("fast");$("#advanced-search").slideToggle("fast");return false})})},init_grid_elements:function(){$(".grid").each(function(){var j=$(this).find("input.grid-row-select-checkbox");var i=$(this).find("span.grid-selected-count");var q=function(){i.text($(j).filter(":checked").length)};$(j).each(function(){$(this).change(q)});q()});if($(".community_rating_star").length!==0){$(".community_rating_star").rating({})}var p=this.grid.attributes;var o=this;$(".page-link > a").each(function(){$(this).click(function(){o.set_page($(this).attr("page_num"));return false})});$(".use-inbound").each(function(){$(this).click(function(i){o.execute({href:$(this).attr("href"),inbound:true});return false})});$(".use-outbound").each(function(){$(this).click(function(i){o.execute({href:$(this).attr("href")});return false})});for(var h in p.items){var k=$("#grid-"+h+"-popup");k.off();var d=new PopupMenu(k);var n=p.items[h];for(var g in p.operations){var e=p.operations[g];var l=e.label;var c=n.operation_config[l];var f=n.encode_id;if(c.allowed&&e.allow_popup){var m={html:e.label,href:c.url_args,target:c.target,confirmation_text:e.confirm,inbound:e.inbound};m.func=function(q){q.preventDefault();var j=$(q.target).html();var i=this.findItemByHtml(j);o.execute(i)};d.addItem(m)}}}},add_filter_condition:function(f,h,c){if(h===""){return false}this.grid.add_filter(f,h,c);var g=$("<span>"+h+"<a href='javascript:void(0);'><span class='delete-search-icon' /></span></a>");g.addClass("text-filter-val");var e=this;g.click(function(){e.grid.remove_filter(f,h);$(this).remove();e.go_page_one();e.execute()});var d=$("#"+f+"-filtering-criteria");d.append(g);this.go_page_one();this.execute()},set_sort_condition:function(h){var g=this.grid.get("sort_key");var f=h;if(g.indexOf(h)!==-1){if(g.substring(0,1)!=="-"){f="-"+h}else{}}$(".sort-arrow").remove();var e=(f.substring(0,1)=="-")?"&uarr;":"&darr;";var c=$("<span>"+e+"</span>").addClass("sort-arrow");var d=$("#"+h+"-header");d.append(c);this.grid.set("sort_key",f);this.go_page_one();this.execute()},set_categorical_filter:function(e,g){var d=this.grid.get("categorical_filters")[e],f=this.grid.get("filters")[e];var c=this;$("."+e+"-filter").each(function(){var k=$.trim($(this).text());var i=d[k];var j=i[e];if(j==g){$(this).empty();$(this).addClass("current-filter");$(this).append(k)}else{if(j==f){$(this).empty();var h=$("<a href='#'>"+k+"</a>");h.click(function(){c.set_categorical_filter(e,j)});$(this).removeClass("current-filter");$(this).append(h)}}});this.grid.add_filter(e,g);this.go_page_one();this.execute()},set_page:function(c){var d=this;$(".page-link").each(function(){var i=$(this).attr("id"),g=parseInt(i.split("-")[2],10),e=d.grid.get("cur_page"),h;if(g===c){h=$(this).children().text();$(this).empty();$(this).addClass("inactive-link");$(this).text(h)}else{if(g===e){h=$(this).text();$(this).empty();$(this).removeClass("inactive-link");var f=$("<a href='#'>"+h+"</a>");f.click(function(){d.set_page(g)});$(this).append(f)}}});if(c==="all"){this.grid.set("cur_page",c)}else{this.grid.set("cur_page",parseInt(c,10))}this.execute()},submit_operation:function(f,g){var e=$('input[name="id"]:checked').length;if(!e>0){return false}var d=$(f).val();var c=[];$("input[name=id]:checked").each(function(){c.push($(this).val())});this.execute({operation:d,id:c,confirmation_text:g});return true},execute:function(l){var f=null;var e=null;var g=null;var c=null;var k=null;if(l){e=l.href;g=l.operation;f=l.id;c=l.confirmation_text;k=l.inbound;if(e!==undefined&&e.indexOf("operation=")!=-1){var j=e.split("?");if(j.length>1){var i=j[1];var d=i.split("&");for(var h=0;h<d.length;h++){if(d[h].indexOf("operation")!=-1){g=d[h].split("=")[1];g=g.replace(/\+/g," ")}else{if(d[h].indexOf("id")!=-1){f=d[h].split("=")[1]}}}}}}if(g&&f){if(c&&c!=""&&c!="None"){if(!confirm(c)){return false}}g=g.toLowerCase();this.grid.set({operation:g,item_ids:f});if(this.grid.can_async_op(g)){this.update_grid()}else{this.go_to(k,"")}return false}if(e){this.go_to(k,e);return false}if(this.grid.get("async")){this.update_grid()}else{this.go_to(k,"")}return false},go_to:function(f,d){var e=this.grid.get("async");this.grid.set("async",false);advanced_search=$("#advanced-search").is(":visible");this.grid.set("advanced_search",advanced_search);if(!d){d=this.grid.get("url_base")+"?"+$.param(this.grid.get_url_data())}this.grid.set({operation:undefined,item_ids:undefined,async:e});if(f){var c=$(".grid-header").closest(".inbound");if(c.length!==0){c.load(d);return}}window.location=d},update_grid:function(){var d=(this.grid.get("operation")?"POST":"GET");$(".loading-elt-overlay").show();var c=this;$.ajax({type:d,url:c.grid.get("url_base"),data:c.grid.get_url_data(),error:function(e){alert("Grid refresh failed")},success:function(f){var e=f.split("*****");$("#grid-table-body").html(e[0]);$("#grid-table-footer").html(e[1]);$("#grid-table-body").trigger("update");$(".loading-elt-overlay").hide();var g=$.trim(e[2]);if(g!==""){$("#grid-message").html(g).show();setTimeout(function(){$("#grid-message").hide()},5000)}},complete:function(){c.grid.set({operation:undefined,item_ids:undefined})}})},check_all_items:function(){var c=document.getElementById("check_all"),d=document.getElementsByTagName("input"),f=0,e;if(c.checked===true){for(e=0;e<d.length;e++){if(d[e].name.indexOf("id")!==-1){d[e].checked=true;f++}}}else{for(e=0;e<d.length;e++){if(d[e].name.indexOf("id")!==-1){d[e].checked=false}}}this.init_grid_elements()},go_page_one:function(){var c=this.grid.get("cur_page");if(c!==null&&c!==undefined&&c!=="all"){this.grid.set("cur_page",1)}}});return{Grid:a,GridView:b}});