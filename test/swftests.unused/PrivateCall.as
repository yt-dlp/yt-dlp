// input: []
// output: 9

package {
public class PrivateCall {
    public static function main():int{
    	var f:OtherClass = new OtherClass();
        return f.func();
    }
}
}

class OtherClass {
	private function pf():int {
		return 9;
	}

	public function func():int {
		return this.pf();
	}
}
