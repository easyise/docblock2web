/**
 * @fileoverview Sample JavaScript file with docblocks for testing
 * @description Contains top-level function, a class, and a jQuery plugin with methods/properties
 * @category Samples
 */

/**
 * @description Adds two numbers together.
 * @param {number} a The first addend.
 * @param {number} b The second addend.
 * @return {number} The sum of both numbers.
 * @example
 * const s = add(2, 3); // 5
 */
function add(a, b) {
  return a + b;
}

/**
 * @description Example ES6 class with instance and static methods and a property.
 * @category Examples
 */
class Greeter {
  /**
   * @description Create a new Greeter.
   * @param {string} name Person's name to store.
   */
  constructor(name) {
    /**
     * @description Stored name.
     * @type {string}
     */
    this.name = name;
  }

  /**
   * @description Produce a greeting string.
   * @return {string} Greeting message.
   */
  greet() {
    return `Hello, ${this.name}!`;
  }

  /**
   * @description Loud greeting helper (static).
   * @param {string} who Person to greet loudly.
   * @return {string}
   */
  static shout(who) {
    return `HEY ${who.toUpperCase()}!`;
  }
}

/**
 * @description Arrow function example that doubles a number.
 * @param {number} value Value to double.
 * @return {number} Doubled value.
 */
const double = value => value * 2;

/**
 * @description jQuery plugin pattern with method registry and defaults.
 * @category jQuery Plugins
 */
(function($){
  /**
   * @description Default configuration values for `myPlugin`.
   * @type {{delay:number, theme:string}}
   */
  var settings = {
    delay: 100,
    theme: 'default'
  };

  /**
   * @description Slice alias used to convert `arguments` into arrays.
   * @type {Function}
   */
  var protoSlice = Array.prototype.slice;

  /**
   * @description Collection of plugin methods addressable by name.
   */
  var methods = {
    /**
     * @description Initialize the plugin on each matched element.
     * @param {Object} options Initialization options.
     * @return {jQuery} Fluent jQuery collection.
     */
    init: function(options) {
      var opts = $.extend({}, settings, options);
      return this.each(function(){
        var $el = $(this);
        $el.data('myPlugin', {
          options: opts,
          initialized: true
        });
      });
    },

    /**
     * @description Example method accepting a parameter.
     * @param {*} a_param Arbitrary input.
     * @return {string} Diagnostic string.
     */
    a_method: function(a_param){
      return 'Handled parameter: ' + a_param;
    }
  };

  /**
   * @description jQuery plugin entry point supporting method dispatch.
   * @param {string|Object=} method Method name or options object.
   * @return {*} Result of the dispatched method.
   */
  $.fn.myPlugin = function(method){

    if (methods[method]) {
      return methods[method].apply(this, protoSlice.call(arguments, 1));
    } else if (typeof method === 'object' || !method) {
      return methods.init.apply(this, arguments);
    } else {
      $.error('Method ' + method + ' does not exist on jQuery.fn.myPlugin');
    }

  };

  /**
   * @description Extend plugin object with static defaults property.
   * @type {{defaults:Object}}
   */
  $.extend($.fn.myPlugin, {
    defaults: settings
  });

})( jQuery );
