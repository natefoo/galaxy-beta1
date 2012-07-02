var ServerStateDeferred=Backbone.Model.extend({defaults:{ajax_settings:{},interval:1000,success_fn:function(a){return true}},go:function(){var d=$.Deferred(),c=this,f=c.get("ajax_settings"),e=c.get("success_fn"),b=c.get("interval"),a=function(){$.ajax(f).success(function(g){if(e(g)){d.resolve(g)}else{setTimeout(a,b)}})};a();return d}});var CanvasManager=function(a){this.default_font=a!==undefined?a:"9px Monaco, Lucida Console, monospace";this.dummy_canvas=this.new_canvas();this.dummy_context=this.dummy_canvas.getContext("2d");this.dummy_context.font=this.default_font;this.char_width_px=this.dummy_context.measureText("A").width;this.patterns={};this.load_pattern("right_strand","/visualization/strand_right.png");this.load_pattern("left_strand","/visualization/strand_left.png");this.load_pattern("right_strand_inv","/visualization/strand_right_inv.png");this.load_pattern("left_strand_inv","/visualization/strand_left_inv.png")};_.extend(CanvasManager.prototype,{load_pattern:function(a,e){var b=this.patterns,c=this.dummy_context,d=new Image();d.src=galaxy_paths.attributes.image_path+e;d.onload=function(){b[a]=c.createPattern(d,"repeat")}},get_pattern:function(a){return this.patterns[a]},new_canvas:function(){var a=$("<canvas/>")[0];if(window.G_vmlCanvasManager){G_vmlCanvasManager.initElement(a)}a.manager=this;return a}});var Cache=Backbone.Model.extend({defaults:{num_elements:20,obj_cache:null,key_ary:null},initialize:function(a){this.clear()},get_elt:function(b){var c=this.attributes.obj_cache,d=this.attributes.key_ary,a=d.indexOf(b);if(a!==-1){if(c[b].stale){d.splice(a,1);delete c[b]}else{this.move_key_to_end(b,a)}}return c[b]},set_elt:function(b,d){var e=this.attributes.obj_cache,f=this.attributes.key_ary,c=this.attributes.num_elements;if(!e[b]){if(f.length>=c){var a=f.shift();delete e[a]}f.push(b)}e[b]=d;return d},move_key_to_end:function(b,a){this.attributes.key_ary.splice(a,1);this.attributes.key_ary.push(b)},clear:function(){this.attributes.obj_cache={};this.attributes.key_ary=[]},size:function(){return this.attributes.key_ary.length}});var GenomeDataManager=Cache.extend({defaults:_.extend({},Cache.prototype.defaults,{dataset:null,filters_manager:null,data_url:null,dataset_state_url:null,data_mode_compatible:function(a,b){return true},can_subset:function(a){return false}}),data_is_ready:function(){var c=this.get("dataset"),b=$.Deferred(),a=new ServerStateDeferred({ajax_settings:{url:this.get("dataset_state_url"),data:{dataset_id:c.id,hda_ldda:c.get("hda_ldda")},dataType:"json"},interval:5000,success_fn:function(d){return d!=="pending"}});$.when(a.go()).then(function(d){b.resolve(d==="ok"||d==="data")});return b},load_data:function(h,g,b,f){var d={chrom:h.get("chrom"),low:h.get("start"),high:h.get("end"),mode:g,resolution:b};dataset=this.get("dataset");if(dataset){d.dataset_id=dataset.id;d.hda_ldda=dataset.get("hda_ldda")}$.extend(d,f);var j=this.get("filters_manager");if(j){var k=[];var a=j.filters;for(var e=0;e<a.length;e++){k.push(a[e].name)}d.filter_cols=JSON.stringify(k)}var c=this;return $.getJSON(this.get("data_url"),d,function(i){c.set_data(h,i)})},get_data:function(g,f,c,e){var h=this.get_elt(g);if(h&&(is_deferred(h)||this.get("data_mode_compatible")(h,f))){return h}var j=this.get("key_ary"),b=this.get("obj_cache"),k,a;for(var d=0;d<j.length;d++){k=j[d];a=new GenomeRegion({from_str:k});if(a.contains(g)){h=b[k];if(is_deferred(h)||(this.get("data_mode_compatible")(h,f)&&this.get("can_subset")(h))){this.move_key_to_end(k,d);return h}}}h=this.load_data(g,f,c,e);this.set_data(g,h);return h},set_data:function(b,a){this.set_elt(b,a)},DEEP_DATA_REQ:"deep",BROAD_DATA_REQ:"breadth",get_more_data:function(i,h,d,g,e){var k=this.get_elt(i);if(!(k&&this.get("data_mode_compatible")(k,h))){console.log("ERROR: no current data for: ",dataset,i.toString(),h,d,g);return}k.stale=true;var c=i.get("start");if(e===this.DEEP_DATA_REQ){$.extend(g,{start_val:k.data.length+1})}else{if(e===this.BROAD_DATA_REQ){c=(k.max_high?k.max_high:k.data[k.data.length-1][2])+1}}var j=i.copy().set("start",c);var b=this,f=this.load_data(j,h,d,g),a=$.Deferred();this.set_data(i,a);$.when(f).then(function(l){if(l.data){l.data=k.data.concat(l.data);if(l.max_low){l.max_low=k.max_low}if(l.message){l.message=l.message.replace(/[0-9]+/,l.data.length)}}b.set_data(i,l);a.resolve(l)});return a},get_elt:function(a){return Cache.prototype.get_elt.call(this,a.toString())},set_elt:function(b,a){return Cache.prototype.set_elt.call(this,b.toString(),a)}});var ReferenceTrackDataManager=GenomeDataManager.extend({load_data:function(a,d,e,b,c){if(b>1){return{data:null}}return GenomeDataManager.prototype.load_data.call(this,a,d,e,b,c)}});var Genome=Backbone.Model.extend({defaults:{name:null,key:null,chroms_info:null},get_chroms_info:function(){return this.attributes.chroms_info.chrom_info}});var GenomeRegion=Backbone.RelationalModel.extend({defaults:{chrom:null,start:0,end:0,DIF_CHROMS:1000,BEFORE:1001,CONTAINS:1002,OVERLAP_START:1003,OVERLAP_END:1004,CONTAINED_BY:1005,AFTER:1006},initialize:function(b){if(b.from_str){var d=b.from_str.split(":"),c=d[0],a=d[1].split("-");this.set({chrom:c,start:parseInt(a[0],10),end:parseInt(a[1],10)})}},copy:function(){return new GenomeRegion({chrom:this.get("chrom"),start:this.get("start"),end:this.get("end")})},length:function(){return this.get("end")-this.get("start")},toString:function(){return this.get("chrom")+":"+this.get("start")+"-"+this.get("end")},toJSON:function(){return{chrom:this.get("chrom"),start:this.get("start"),end:this.get("end")}},compute_overlap:function(h){var b=this.get("chrom"),g=h.get("chrom"),f=this.get("start"),d=h.get("start"),e=this.get("end"),c=h.get("end"),a;if(b&&g&&b!==g){return this.get("DIF_CHROMS")}if(f<d){if(e<d){a=this.get("BEFORE")}else{if(e<=c){a=this.get("OVERLAP_START")}else{a=this.get("CONTAINS")}}}else{if(f>c){a=this.get("AFTER")}else{if(e<=c){a=this.get("CONTAINED_BY")}else{a=this.get("OVERLAP_END")}}}return a},contains:function(a){return this.compute_overlap(a)===this.get("CONTAINS")},overlaps:function(a){return _.intersection([this.compute_overlap(a)],[this.get("DIF_CHROMS"),this.get("BEFORE"),this.get("AFTER")]).length===0}});var GenomeRegionCollection=Backbone.Collection.extend({model:GenomeRegion});var BrowserBookmark=Backbone.Model.extend({defaults:{region:null,note:""}});var BrowserBookmarks=Backbone.Collection.extend({model:BrowserBookmark});var Visualization=Backbone.RelationalModel.extend({defaults:{id:"",title:"",type:"",dbkey:"",datasets:[]},url:function(){return galaxy_paths.get("visualization_url")},save:function(){return $.ajax({url:this.url(),type:"POST",dataType:"json",data:{vis_json:JSON.stringify(this)}})}});var TracksterVisualization=Visualization.extend({defaults:{bookmarks:[],viewport:{}}});var CircsterVisualization=Visualization.extend({});var HistogramDataset=Backbone.Model.extend({initialize:function(a){this.attributes.data=a;this.attributes.max=_.max(a,function(b){if(!b||typeof b==="string"){return 0}return b[1]})[1]}});var TrackConfig=Backbone.Model.extend({});var CircsterHistogramDatasetLayout=Backbone.Model.extend({chroms_layout:function(){var b=this.attributes.genome.get_chroms_info(),d=d3.layout.pie().value(function(f){return f.len}).sort(null),e=d(b),a=this.attributes.total_gap/b.length,c=_.map(e,function(h,g){var f=h.endAngle-a;h.endAngle=(f>h.startAngle?f:h.startAngle);return h});return c},chrom_data_layout:function(j,b,g,f,h){if(!b||typeof b==="string"){return null}var d=b[0],i=b[3],c=d3.scale.linear().domain([0,h]).range([g,f]),e=d3.layout.pie().value(function(k){return i}).startAngle(j.startAngle).endAngle(j.endAngle),a=e(d);_.each(d,function(k,l){a[l].outerRadius=c(k[1])});return a}});var CircsterView=Backbone.View.extend({className:"circster",initialize:function(a){this.width=a.width;this.height=a.height;this.total_gap=a.total_gap;this.genome=a.genome;this.dataset=a.dataset;this.radius_start=a.radius_start;this.dataset_arc_height=a.dataset_arc_height},render:function(){var d=this.radius_start,e=this.dataset_arc_height,j=new CircsterHistogramDatasetLayout({genome:this.genome,total_gap:this.total_gap}),i=j.chroms_layout(),g=_.zip(i,this.dataset.attributes.data),h=this.dataset.attributes.max,b=_.map(g,function(m){var n=m[0],l=m[1];return j.chrom_data_layout(n,l,d,d+e,h)});var c=d3.select(this.$el[0]).append("svg").attr("width",this.width).attr("height",this.height).append("g").attr("transform","translate("+this.width/2+","+this.height/2+")");var k=c.append("g").attr("id","inner-arc"),f=d3.svg.arc().innerRadius(d).outerRadius(d+e),a=k.selectAll("#inner-arc>path").data(i).enter().append("path").attr("d",f).style("stroke","#ccc").style("fill","#ccc").append("title").text(function(l){return l.data.chrom});_.each(b,function(l){if(!l){return}var o=c.append("g"),n=d3.svg.arc().innerRadius(d),m=o.selectAll("path").data(l).enter().append("path").attr("d",n).style("stroke","red").style("fill","red")})}});var TrackBrowserRouter=Backbone.Router.extend({initialize:function(b){this.view=b.view;this.route(/([\w]+)$/,"change_location");this.route(/([\w]+\:[\d,]+-[\d,]+)$/,"change_location");var a=this;a.view.on("navigate",function(c){a.navigate(c)})},change_location:function(a){this.view.go_to(a)}});var add_datasets=function(a,c,b){$.ajax({url:a,data:{"f-dbkey":view.dbkey},error:function(){alert("Grid failed")},success:function(d){show_modal("Select datasets for new tracks",d,{Cancel:function(){hide_modal()},Add:function(){var e=[];$("input[name=id]:checked,input[name=ldda_ids]:checked").each(function(){var f,g=$(this).val();if($(this).attr("name")==="id"){f={hda_id:g}}else{f={ldda_id:g}}e[e.length]=$.ajax({url:c,data:f,dataType:"json"})});$.when.apply($,e).then(function(){var f=(arguments[0] instanceof Array?$.map(arguments,function(g){return g[0]}):[arguments[0]]);b(f)});hide_modal()}})}})};