# 求む...！リファクタリング...！！
このBOT、徹夜で書いたやつだからリファクタがまるでされていません。
有志たち、リファクタ頼んだ！

# これはなに
都道府県名を送信すると、その都道府県の新型コロナウイルス感染症関連のデータが得られるLINE BOTです。

## 現時点で得られるデータ
* 総感染者数
* 男女別感染者数
* 年代別感染者数
これの他に、様々なデータを取得できるようにしたいと考えております。

# 使用方法
以下のQRコードを読み込んでLINEアカウントを登録してください(LINEアプリに飛びます)。
![](https://i.imgur.com/kFPk4G3.png)

# 環境構築
`pipenv install`を実行してください。

# システム構成
![](https://i.imgur.com/1fdBENd.jpg)

# ブランチの運用方法
プルリクエストはdevelopブランチによろしくお願いします。
masterにマージされると、HEROKUに自動でデプロイされるようになっています。
