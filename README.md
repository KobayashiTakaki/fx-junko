# バーチャルFXトレーダー純子ちゃんBot
* 紹介記事 <https://takakisan.com/fx-auto-trade-python/>

# これは何か？
Pythonで作成したFX自動取引ツール＆Twitter botです。  
こちらのアカウントでトレードを実況しています。  
[@fx_junko](https://twitter.com/fx_junko)

# 仕組み
OANDAというFX会社の提供しているWeb APIを利用して、価格データの取得、トレードを行います。  
5分足のローソクデータを定期的に取得し、それを元に売り買いの注文を実行します。  
売り買いのタイミングでTwitterに投稿します。

# 主に使用したライブラリ
* v20 ... OANDAが提供しているWeb APIのPython用ラッパー
* pandas ... 価格データの整形、分析に使用
* schedule ... スケジュール、ループ実行に使用

# 儲かるのか？
儲かってません。

※本プログラムにより生じた損害について、作者は一切の責任を負いません。
