;(function ($) {
  var _ajax = $.ajax
  $.ajax = function (options) {
    var fn = {
      error: function (XMLHttpRequest, textStatus, errorThrown) {
        // toastr.error(XMLHttpRequest.responseText, '错误消息', { closeButton: true, timeOut: 0, positionClass: 'toast-top-full-width' });
      },
      success: function (data, textStatus) {},
      beforeSend: function (XHR) {},
      complete: function (XHR, TS) {}
    }
    // 3.扩展原生的$.ajax方法，返回最新的参数
    var _options = $.extend(
      {},
      {
        error: function (XMLHttpRequest, textStatus, errorThrown) {
          fn.error(XMLHttpRequest, textStatus, errorThrown)
        },
        success: function (data, textStatus) {
          fn.success(data, textStatus)
        },
        beforeSend: function (XHR, jqXHR) {
          var url = jqXHR.url
          if (url.indexOf('?') != -1) {
            if (url.indexOf('ecph_manager') != -1) {
              url = url.substring(
                url.indexOf('/ecph_manager') + 13,
                url.indexOf('?')
              )
            } else {
              url = url.substring(url.indexOf('/ecph') + 5, url.indexOf('?'))
            }
          } else {
            if (url.indexOf('ecph_manager') != -1) {
              url = url.substring(url.indexOf('/ecph_manager') + 13, url.length)
            } else {
              url = url.substring(url.indexOf('/ecph') + 5, url.length)
            }
          }
          XHR.setRequestHeader('token', hex_md5(token + url))
          fn.beforeSend(XHR)
        },
        complete: function (XHR, TS) {
          fn.complete(XHR, TS)
        }
      },
      options
    )
    _ajax(_options)
  }
  function getCookie (name) {
    var arr = document.cookie.match(
      new RegExp('(^| )' + name + '=([^;]*)(;|$)')
    )
    if (arr != null) return unescape(arr[2])
    return null
  }
})(jQuery)
