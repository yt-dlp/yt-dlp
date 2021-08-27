// input: []
// output: 9

package {
public class PrivateVoidCall {
    public static function main():int{
        var f:OtherClass = new OtherClass();
        f.func();
        return 9;
    }
}
}

class OtherClass {
    private function pf():void {
        ;
    }

    public function func():void {
        this.pf();
    }
}
