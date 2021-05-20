# PSO2LogReader

## これはなに

オンラインゲームPSO2のログファイルをリアルタイムで読み取り、棒読みちゃんに喋らせるソフトウェアです。

+ チャットの読み上げ
+ シンボルアート表示の読み上げ（「〇〇のシンボルアート」）
+ ロビーアクションの読み上げ（「〇〇が△△した」）
+ ロビーアクションのチケット名表示
+ 取得アイテムの集計と読み上げ
+ 特定アイテムを獲得したときにサウンドを再生 （カスタマイズ可能）
+ 獲得した報酬アイテム名をクリップボードへコピー
+ カジノコインのグラフ表示

## Python環境の準備

1. Pythonのインストール

このプログラムを実行するには Python 3.xx が必要です。
<https://www.python.jp/install/windows/install.html>

2. モジュールのインストール

<install.bat>を実行してください。

## 使い方

<PSO2LogReader.pyw>をダブルクリックすれば起動します。

## 関連ファイルについて

### spitem.txt

アイテムを獲得した時に再生するサウンドの設定を記述するファイルです。

+ 行頭が # で始まる行はコメント行
+ 鍵括弧[]でwav/mp3ファイルを宣言
+ 宣言後の行で鳴らしたい対象のアイテム名を記述
+ スラッシュ / で囲えば正規表現
+ <spitem.txt>はいつでも編集でき、結果は即時反映されます。

## 棒読みちゃん

棒読みちゃんは次のURLから入手できます。
<https://chi.usamimi.info/Program/Application/BouyomiChan/>

棒読みちゃんと連携するための設定等は特にありませんが、起動させる必要はあります。
※当ソフトウェアから棒読みちゃんを起動することはしません。
