# PSO2LogReader

## これはなに

オンラインゲームPSO2のログファイルをリアルタイムで読み取り、棒読みちゃんに喋らせるソフトウェアです。

+ チャットの読み上げ
+ シンボルアート表示の読み上げ（「〇〇のシンボルアート」）
+ ロビーアクションの読み上げ（「〇〇が△△した」）
+ ロビーアクションのチケット名表示
+ 特定アイテムを獲得したときにサウンドを再生
+ 獲得した報酬アイテム名をクリップボードへコピー

## 使い方

<logreader.exe>を実行してください。

Python環境をお持ちの方は後述の依存モジュールをインストールして<logreader.py>を実行してください。

## spitem.txt

アイテムを獲得した時に再生するサウンドの設定を記述するファイルです。

+ 行頭が # で始まる行はコメント行
+ [] でwavファイルを宣言
+ 宣言後の行で鳴らしたい対象のアイテム名を記述
+ スラッシュ / で囲えば正規表現
+ <spitem.txt>はいつでも編集でき、結果は即時反映されます。

## 棒読みちゃん

棒読みちゃんは次のURLから入手できます。
<https://chi.usamimi.info/Program/Application/BouyomiChan/>

棒読みちゃんと連携するための設定等は特にありませんが、起動しておく必要はあります。

## 依存モジュール

```
pip3 install https://github.com/yumimint/bouyomichan/releases/download/0.1.0/bouyomichan-0.1.0.tar.gz
pip3 install watchdog colorama playsound pyperclip
```
